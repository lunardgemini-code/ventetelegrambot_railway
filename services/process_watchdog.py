"""Independent liveness watchdog for the Railway web process."""

from __future__ import annotations

import argparse
import faulthandler
from http.client import HTTPConnection
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit


logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class WatchdogConfig:
    enabled: bool = True
    startup_grace_seconds: float = 20.0
    interval_seconds: float = 10.0
    request_timeout_seconds: float = 3.0
    failure_threshold: int = 3
    diagnostic_delay_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "WatchdogConfig":
        return cls(
            enabled=_env_bool("PROCESS_WATCHDOG_ENABLED", True),
            startup_grace_seconds=_env_float(
                "PROCESS_WATCHDOG_STARTUP_GRACE_SECONDS", 20.0, 0.0
            ),
            interval_seconds=_env_float(
                "PROCESS_WATCHDOG_INTERVAL_SECONDS", 10.0, 1.0
            ),
            request_timeout_seconds=_env_float(
                "PROCESS_WATCHDOG_TIMEOUT_SECONDS", 3.0, 0.5
            ),
            failure_threshold=_env_int(
                "PROCESS_WATCHDOG_FAILURE_THRESHOLD", 3, 2
            ),
            diagnostic_delay_seconds=_env_float(
                "PROCESS_WATCHDOG_DIAGNOSTIC_DELAY_SECONDS", 2.0, 0.0
            ),
        )


def enable_fault_diagnostics() -> bool:
    """Allow the watchdog to dump every Python thread before a forced restart."""
    try:
        faulthandler.enable(all_threads=True)
        diagnostic_signal = getattr(signal, "SIGUSR2", None)
        if diagnostic_signal is not None:
            faulthandler.register(
                diagnostic_signal,
                all_threads=True,
                chain=False,
            )
        return True
    except (OSError, RuntimeError, ValueError):
        logger.warning("Python fault diagnostics could not be enabled", exc_info=True)
        return False


def probe_liveness(url: str, timeout_seconds: float) -> bool:
    parsed = urlsplit(url)
    connection = HTTPConnection(
        parsed.hostname or "127.0.0.1",
        parsed.port or 80,
        timeout=timeout_seconds,
    )
    try:
        connection.request(
            "GET",
            parsed.path or "/",
            headers={"User-Agent": "VenteBot-Process-Watchdog/1.0"},
        )
        response = connection.getresponse()
        response.read()
        return 200 <= int(response.status) < 300
    except Exception:
        return False
    finally:
        connection.close()


def parent_is_alive(parent_pid: int) -> bool:
    try:
        os.kill(parent_pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def resolve_restart_target_pid(parent_pid: int) -> int:
    """Target PID 1 on Railway so a watchdog restart stops the whole container."""
    railway_runtime = any(
        os.environ.get(name)
        for name in (
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_PUBLIC_DOMAIN",
        )
    )
    return 1 if railway_runtime else int(parent_pid)


def _stderr_log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def monitor_parent(
    parent_pid: int,
    port: int,
    config: WatchdogConfig,
    *,
    probe: Callable[[str, float], bool] = probe_liveness,
    is_alive: Callable[[int], bool] = parent_is_alive,
    send_signal: Callable[[int, int], None] = os.kill,
    sleeper: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = _stderr_log,
    diagnostic_signal: int | None = None,
    kill_signal: int | None = None,
    restart_pid: int | None = None,
) -> int:
    """Monitor the parent without sharing its interpreter or event loop."""
    if not is_alive(parent_pid):
        return 0

    if config.startup_grace_seconds:
        sleeper(config.startup_grace_seconds)

    url = f"http://127.0.0.1:{int(port)}/health/live"
    failures = 0
    diagnostic_signal = (
        getattr(signal, "SIGUSR2", None)
        if diagnostic_signal is None
        else diagnostic_signal
    )
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM) if kill_signal is None else kill_signal
    restart_pid = int(parent_pid if restart_pid is None else restart_pid)

    while is_alive(parent_pid):
        healthy = False
        try:
            healthy = probe(url, config.request_timeout_seconds)
        except Exception:
            healthy = False

        if healthy:
            if failures:
                log("Process watchdog: liveness recovered; failure counter reset")
            failures = 0
        else:
            failures += 1
            log(
                "Process watchdog: liveness failure "
                f"{failures}/{config.failure_threshold}"
            )
            if failures >= config.failure_threshold:
                log(
                    "Process watchdog: event loop is unresponsive; "
                    "capturing diagnostics and restarting the container"
                )
                if diagnostic_signal is not None:
                    try:
                        send_signal(parent_pid, diagnostic_signal)
                    except (ProcessLookupError, PermissionError, OSError):
                        return 0
                if config.diagnostic_delay_seconds:
                    sleeper(config.diagnostic_delay_seconds)
                # On Railway the Python process may be wrapped by PID 1. Kill
                # PID 1 even if Python disappeared while diagnostics ran, so
                # the platform observes a real container failure and applies
                # its restart policy.
                if restart_pid != parent_pid or is_alive(parent_pid):
                    try:
                        log(
                            "Process watchdog: terminating restart target "
                            f"PID {restart_pid}"
                        )
                        send_signal(restart_pid, kill_signal)
                    except (ProcessLookupError, PermissionError, OSError):
                        return 0
                return 2

        sleeper(config.interval_seconds)

    return 0


def start_process_watchdog(
    parent_pid: int,
    port: int,
    config: WatchdogConfig | None = None,
    *,
    popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
) -> subprocess.Popen | None:
    config = config or WatchdogConfig.from_env()
    if not config.enabled:
        logger.info("Process watchdog is disabled")
        return None

    command = [
        sys.executable,
        "-u",
        str(Path(__file__).resolve()),
        "--monitor",
        "--parent-pid",
        str(int(parent_pid)),
        "--restart-pid",
        str(resolve_restart_target_pid(parent_pid)),
        "--port",
        str(int(port)),
        "--startup-grace",
        str(config.startup_grace_seconds),
        "--interval",
        str(config.interval_seconds),
        "--timeout",
        str(config.request_timeout_seconds),
        "--failures",
        str(config.failure_threshold),
        "--diagnostic-delay",
        str(config.diagnostic_delay_seconds),
    ]
    process = popen_factory(
        command,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    logger.info(
        "Process watchdog started (pid=%s, parent_pid=%s, restart_pid=%s)",
        process.pid,
        parent_pid,
        resolve_restart_target_pid(parent_pid),
    )
    return process


def stop_process_watchdog(
    process: subprocess.Popen | None,
    timeout_seconds: float = 3.0,
) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout_seconds)
    except OSError:
        pass


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor a VenteBot web process")
    parser.add_argument("--monitor", action="store_true", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--restart-pid", type=int)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--startup-grace", type=float, required=True)
    parser.add_argument("--interval", type=float, required=True)
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("--failures", type=int, required=True)
    parser.add_argument("--diagnostic-delay", type=float, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = WatchdogConfig(
        enabled=True,
        startup_grace_seconds=max(0.0, args.startup_grace),
        interval_seconds=max(1.0, args.interval),
        request_timeout_seconds=max(0.5, args.timeout),
        failure_threshold=max(2, args.failures),
        diagnostic_delay_seconds=max(0.0, args.diagnostic_delay),
    )
    return monitor_parent(
        args.parent_pid,
        args.port,
        config,
        restart_pid=args.restart_pid,
    )


if __name__ == "__main__":
    raise SystemExit(main())
