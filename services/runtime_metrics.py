"""Lightweight dependency, event-loop, and process metrics.

The module deliberately keeps all samples in memory. It is used to decide
whether webhook concurrency is safe to increase, not as a full monitoring
system.
"""

from __future__ import annotations

import asyncio
from collections import Counter, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
import sys
import time
from typing import AsyncIterator


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


_DEPENDENCY_LIMITS = {
    "binance": _env_int("BINANCE_CONCURRENCY", 4),
    "nowpayments": _env_int("NOWPAYMENTS_CONCURRENCY", 4),
    "supplier": _env_int("SUPPLIER_CONCURRENCY", 3),
    "sports": _env_int("SPORTS_API_CONCURRENCY", 2),
    "blockchain": _env_int("BLOCKCHAIN_API_CONCURRENCY", 3),
}
_CIRCUIT_FAILURE_THRESHOLD = _env_int("EXTERNAL_CIRCUIT_FAILURES", 5, 2)
_CIRCUIT_COOLDOWN_SECONDS = _env_float("EXTERNAL_CIRCUIT_COOLDOWN_SECONDS", 15.0, 1.0)
_DEPENDENCY_QUEUE_TIMEOUT_SECONDS = _env_float(
    "EXTERNAL_QUEUE_TIMEOUT_SECONDS", 5.0, 0.5
)

_EXTERNAL_SAMPLES = deque(maxlen=10000)
_LOOP_LAG_SAMPLES = deque(maxlen=5000)
_MEMORY_SAMPLES = deque(maxlen=5000)
_SEMAPHORES: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Semaphore]] = {}
_DEPENDENCY_ACTIVE = Counter()
_DEPENDENCY_WAITERS = Counter()


@dataclass
class _CircuitState:
    failures: int = 0
    opened_until: float = 0.0


_CIRCUITS: dict[str, _CircuitState] = {}


class DependencyCircuitOpen(RuntimeError):
    """Raised when a failing dependency is inside its short cooldown."""


def _dependency_family(name: str) -> str:
    return str(name or "external").split(":", 1)[0]


def _limit_for(name: str) -> int:
    family = _dependency_family(name)
    return _DEPENDENCY_LIMITS.get(family, 3)


def _semaphore_for(name: str) -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    family = _dependency_family(name)
    current = _SEMAPHORES.get(family)
    if current is None or current[0] is not loop:
        semaphore = asyncio.Semaphore(_limit_for(name))
        _SEMAPHORES[family] = (loop, semaphore)
        return semaphore
    return current[1]


def _retryable_failure(exc: BaseException) -> bool:
    retryable = getattr(exc, "retryable", None)
    if retryable is not None:
        return bool(retryable)
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        try:
            return int(status_code) == 429 or int(status_code) >= 500
        except (TypeError, ValueError):
            pass
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return any(token in name or token in message for token in (
        "timeout", "network", "connect", "unreachable", "temporarily"
    ))


@asynccontextmanager
async def dependency_call(
    name: str,
    *,
    circuit_breaker: bool = True,
) -> AsyncIterator[None]:
    """Limit one dependency family and record latency without hiding errors."""
    dependency = str(name or "external")[:60]
    now = time.monotonic()
    circuit = _CIRCUITS.setdefault(dependency, _CircuitState())
    if circuit_breaker and circuit.opened_until > now:
        _EXTERNAL_SAMPLES.append((now, dependency, 0.0, False, False, True))
        raise DependencyCircuitOpen(
            f"{dependency} circuit is cooling down for "
            f"{max(1, int(circuit.opened_until - now))}s"
        )

    semaphore = _semaphore_for(dependency)
    family = _dependency_family(dependency)
    _DEPENDENCY_WAITERS[family] += 1
    acquired = False
    started_at = time.monotonic()
    try:
        await asyncio.wait_for(
            semaphore.acquire(), timeout=_DEPENDENCY_QUEUE_TIMEOUT_SECONDS
        )
        acquired = True
    except TimeoutError:
        _EXTERNAL_SAMPLES.append(
            (time.monotonic(), dependency, time.monotonic() - started_at, False, True, False)
        )
        raise
    finally:
        _DEPENDENCY_WAITERS[family] = max(0, _DEPENDENCY_WAITERS[family] - 1)

    _DEPENDENCY_ACTIVE[family] += 1
    call_started_at = time.monotonic()
    try:
        yield
    except BaseException as exc:
        timed_out = isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in type(exc).__name__.lower()
        retryable = _retryable_failure(exc)
        _EXTERNAL_SAMPLES.append(
            (time.monotonic(), dependency, time.monotonic() - call_started_at, False, timed_out, False)
        )
        if circuit_breaker and retryable:
            circuit.failures += 1
            if circuit.failures >= _CIRCUIT_FAILURE_THRESHOLD:
                circuit.opened_until = time.monotonic() + _CIRCUIT_COOLDOWN_SECONDS
        raise
    else:
        _EXTERNAL_SAMPLES.append(
            (time.monotonic(), dependency, time.monotonic() - call_started_at, True, False, False)
        )
        circuit.failures = 0
        circuit.opened_until = 0.0
    finally:
        _DEPENDENCY_ACTIVE[family] = max(0, _DEPENDENCY_ACTIVE[family] - 1)
        if acquired:
            semaphore.release()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[index]


def _rss_mb() -> float:
    """Read current RSS on Linux, with a dependency-free fallback elsewhere."""
    try:
        with open("/proc/self/statm", "r", encoding="ascii") as handle:
            resident_pages = int(handle.read().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
    except (OSError, ValueError, IndexError, AttributeError):
        try:
            import resource

            rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if sys.platform == "darwin":
                rss /= 1024
            return rss / 1024
        except Exception:
            return 0.0


async def runtime_health_monitor(interval_seconds: float = 0.5) -> None:
    """Measure event-loop scheduling lag and process memory continuously."""
    interval = max(0.1, float(interval_seconds))
    expected = time.monotonic() + interval
    while True:
        await asyncio.sleep(interval)
        now = time.monotonic()
        _LOOP_LAG_SAMPLES.append((now, max(0.0, now - expected)))
        _MEMORY_SAMPLES.append((now, _rss_mb()))
        expected = now + interval


def get_runtime_snapshot(window_seconds: int = 300) -> dict:
    now = time.monotonic()
    cutoff = now - max(10, int(window_seconds))
    samples = [sample for sample in _EXTERNAL_SAMPLES if sample[0] >= cutoff]
    grouped: dict[str, list[tuple]] = {}
    for sample in samples:
        grouped.setdefault(sample[1], []).append(sample)
    dependencies = []
    for name, dependency_samples in grouped.items():
        durations = [sample[2] for sample in dependency_samples]
        circuit = _CIRCUITS.get(name) or _CircuitState()
        dependencies.append({
            "name": name,
            "calls": len(dependency_samples),
            "errors": sum(1 for sample in dependency_samples if not sample[3]),
            "timeouts": sum(1 for sample in dependency_samples if sample[4]),
            "circuit_rejections": sum(1 for sample in dependency_samples if sample[5]),
            "average_ms": round(sum(durations) / len(durations) * 1000, 1),
            "p95_ms": round(_percentile(durations, 0.95) * 1000, 1),
            "max_ms": round(max(durations, default=0) * 1000, 1),
            "circuit_open": circuit.opened_until > now,
        })
    dependencies.sort(key=lambda item: (item["p95_ms"], item["calls"]), reverse=True)

    lags = [sample[1] for sample in _LOOP_LAG_SAMPLES if sample[0] >= cutoff]
    memories = [sample[1] for sample in _MEMORY_SAMPLES if sample[0] >= cutoff]
    external_durations = [sample[2] for sample in samples]
    return {
        "external_apis": {
            "calls": len(samples),
            "errors": sum(1 for sample in samples if not sample[3]),
            "timeouts": sum(1 for sample in samples if sample[4]),
            "p95_ms": round(_percentile(external_durations, 0.95) * 1000, 1),
            "dependencies": dependencies,
            "limits": dict(_DEPENDENCY_LIMITS),
            "active": dict(_DEPENDENCY_ACTIVE),
            "waiters": dict(_DEPENDENCY_WAITERS),
        },
        "event_loop": {
            "samples": len(lags),
            "average_lag_ms": round(sum(lags) / len(lags) * 1000, 1) if lags else 0.0,
            "p95_lag_ms": round(_percentile(lags, 0.95) * 1000, 1),
            "max_lag_ms": round(max(lags, default=0) * 1000, 1),
        },
        "memory": {
            "rss_mb": round(memories[-1], 1) if memories else round(_rss_mb(), 1),
            "max_rss_mb": round(max(memories, default=0), 1),
        },
    }


def reset_runtime_metrics_for_tests() -> None:
    _EXTERNAL_SAMPLES.clear()
    _LOOP_LAG_SAMPLES.clear()
    _MEMORY_SAMPLES.clear()
    _CIRCUITS.clear()
    _DEPENDENCY_ACTIVE.clear()
    _DEPENDENCY_WAITERS.clear()
    _SEMAPHORES.clear()
