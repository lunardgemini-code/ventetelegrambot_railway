"""Small PID 1 supervisor that restarts the bot after an unexpected exit."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


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
class SupervisorConfig:
    restart_delay_seconds: float = 2.0
    max_restarts: int = 5
    restart_window_seconds: float = 600.0

    @classmethod
    def from_env(cls) -> "SupervisorConfig":
        return cls(
            restart_delay_seconds=_env_float(
                "PROCESS_SUPERVISOR_RESTART_DELAY_SECONDS", 2.0, 0.0
            ),
            max_restarts=_env_int("PROCESS_SUPERVISOR_MAX_RESTARTS", 5, 1),
            restart_window_seconds=_env_float(
                "PROCESS_SUPERVISOR_RESTART_WINDOW_SECONDS", 600.0, 30.0
            ),
        )


def _log(message: str) -> None:
    print(f"Process supervisor: {message}", file=sys.stderr, flush=True)


def supervise(
    config: SupervisorConfig | None = None,
    *,
    popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    install_signal_handlers: bool = True,
    log: Callable[[str], None] = _log,
) -> int:
    """Run the bot and restart it unless the supervisor is shutting down."""
    config = config or SupervisorConfig.from_env()
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-u", str(root / "bot.py")]
    restart_times: deque[float] = deque()
    stopping = False
    child: subprocess.Popen | None = None
    previous_handlers: dict[int, object] = {}

    def request_stop(signum, _frame) -> None:
        nonlocal stopping
        stopping = True
        if child is not None and child.poll() is None:
            try:
                child.terminate()
            except OSError:
                pass

    if install_signal_handlers:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, request_stop)

    try:
        while not stopping:
            child = popen_factory(command, cwd=str(root))
            log(f"bot started pid={child.pid}")
            exit_code = int(child.wait())
            child = None

            if stopping:
                return 0

            now = clock()
            cutoff = now - config.restart_window_seconds
            while restart_times and restart_times[0] < cutoff:
                restart_times.popleft()
            restart_times.append(now)

            if len(restart_times) > config.max_restarts:
                log(
                    "restart budget exhausted; exiting so Railway can replace "
                    "the container"
                )
                return exit_code if exit_code != 0 else 1

            log(
                f"bot exited unexpectedly with code {exit_code}; restarting "
                f"{len(restart_times)}/{config.max_restarts} in "
                f"{config.restart_delay_seconds:.1f}s"
            )
            sleeper(config.restart_delay_seconds)
    finally:
        if child is not None and child.poll() is None:
            try:
                child.terminate()
            except OSError:
                pass
        if install_signal_handlers:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)

    return 0


def main() -> int:
    return supervise()


if __name__ == "__main__":
    raise SystemExit(main())
