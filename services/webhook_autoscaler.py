"""Adaptive and reversible webhook worker management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
import inspect
import logging
import os
import time
from typing import Awaitable, Callable


logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


class AutoscaleState(str, Enum):
    CALM = "CALM"
    PRESSURE = "PRESSURE"
    CRITICAL = "CRITICAL"
    RECOVERY = "RECOVERY"
    BOTTLENECK = "BOTTLENECK"


@dataclass
class AutoscaleConfig:
    enabled: bool = True
    observe_only: bool = True
    min_workers: int = 8
    max_workers: int = 20
    initial_workers: int = 8
    calm_seconds_before_downscale: int = 300
    pressure_confirmations: int = 2
    scale_up_cooldown_seconds: int = 15
    recovery_seconds: int = 120
    memory_limit_mb: int = 450

    @classmethod
    def from_env(cls) -> "AutoscaleConfig":
        minimum = _env_int("WEBHOOK_WORKERS_MIN", 8)
        maximum = max(minimum, _env_int("WEBHOOK_WORKERS_MAX", 20))
        initial = min(maximum, max(minimum, _env_int("WEBHOOK_WORKERS_INITIAL", 8)))
        return cls(
            enabled=_env_bool("WEBHOOK_AUTOSCALE_ENABLED", True),
            observe_only=_env_bool("WEBHOOK_AUTOSCALE_OBSERVE_ONLY", True),
            min_workers=minimum,
            max_workers=maximum,
            initial_workers=initial,
            calm_seconds_before_downscale=_env_int("WEBHOOK_AUTOSCALE_CALM_SECONDS", 300, 30),
            pressure_confirmations=_env_int("WEBHOOK_AUTOSCALE_PRESSURE_SAMPLES", 2, 1),
            scale_up_cooldown_seconds=_env_int("WEBHOOK_AUTOSCALE_UP_COOLDOWN_SECONDS", 15, 1),
            recovery_seconds=_env_int("WEBHOOK_AUTOSCALE_RECOVERY_SECONDS", 120, 10),
            memory_limit_mb=_env_int("WEBHOOK_AUTOSCALE_MEMORY_LIMIT_MB", 450, 64),
        )

    def clamp(self, workers: int) -> int:
        return min(self.max_workers, max(self.min_workers, int(workers)))


@dataclass
class AutoscaleDecision:
    state: AutoscaleState
    bottleneck: str
    current_workers: int
    target_workers: int
    reason: str
    next_analysis_seconds: int
    apply: bool = False
    emergency: bool = False


class AutoscaleDecisionEngine:
    """Pure state machine; worker lifecycle is handled by the manager."""

    def __init__(self, config: AutoscaleConfig, *, clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.clock = clock
        self.state = AutoscaleState.CALM
        self.pressure_count = 0
        self.calm_since: float | None = None
        self.last_scale_at = 0.0
        self.last_pressure_at = 0.0
        self.emergency_used = False

    def _dependency_bottleneck(self, snapshot: dict) -> str | None:
        database = snapshot.get("database") or {}
        writes = database.get("write_serialization") or {}
        if (
            int(database.get("connection_errors") or 0) > 0
            or float(database.get("p95_ms") or 0) >= 750
            or int(writes.get("timeouts") or 0) > 0
            or float(writes.get("p95_wait_ms") or 0) >= 750
        ):
            return "database"
        event_loop = snapshot.get("event_loop") or {}
        if (
            float(event_loop.get("p95_lag_ms") or 0) >= 250
            or float(event_loop.get("max_lag_ms") or 0) >= 1000
        ):
            return "event_loop"
        memory = snapshot.get("memory") or {}
        if float(memory.get("rss_mb") or 0) >= self.config.memory_limit_mb:
            return "memory"
        external = snapshot.get("external_apis") or {}
        calls = int(external.get("calls") or 0)
        errors = int(external.get("errors") or 0)
        if calls >= 3 and (
            float(external.get("p95_ms") or 0) >= 3000
            or int(external.get("timeouts") or 0) > 0
            or errors / max(1, calls) >= 0.4
        ):
            return "external_api"
        queue = snapshot.get("queue") or {}
        if (
            int(queue.get("max_user_backlog") or 0) >= 5
            and float(queue.get("largest_user_share") or 0) >= 0.7
        ):
            return "single_user_backlog"
        return None

    def evaluate(self, snapshot: dict, current_workers: int) -> AutoscaleDecision:
        now = self.clock()
        current = self.config.clamp(current_workers)
        queue = snapshot.get("queue") or {}
        traffic = snapshot.get("traffic") or {}
        workers = snapshot.get("workers") or {}
        samples = int(traffic.get("processed_5m") or 0)
        occupancy = float(workers.get("utilization_1m") or 0)
        queue_wait = float(queue.get("p95_wait_ms") or 0)
        queue_current = int(queue.get("current") or 0)
        queue_peak = int(queue.get("peak_5m") or 0)
        queue_rising = bool(queue.get("rising"))
        dependency = self._dependency_bottleneck(snapshot)

        if dependency:
            self.state = AutoscaleState.BOTTLENECK
            self.pressure_count = 0
            self.calm_since = None
            return AutoscaleDecision(
                self.state,
                dependency,
                current,
                current,
                f"{dependency} is limiting throughput; worker growth is blocked",
                30,
            )

        if samples < 20:
            self.state = AutoscaleState.CALM
            self.pressure_count = 0
            return AutoscaleDecision(
                self.state,
                "insufficient_data",
                current,
                current,
                "At least 20 recent updates are required",
                60,
            )

        critical = queue_current > 50 and occupancy >= 0.95
        pressure = queue_wait >= 500 and occupancy >= 0.8 and queue_rising
        if critical:
            self.state = AutoscaleState.CRITICAL
            self.calm_since = None
            self.last_pressure_at = now
            target = current
            if not self.emergency_used and now - self.last_scale_at >= self.config.scale_up_cooldown_seconds:
                target = self.config.clamp(current + 4)
                self.emergency_used = target > current
                if target > current:
                    self.last_scale_at = now
            return AutoscaleDecision(
                self.state,
                "workers",
                current,
                target,
                "Queue above 50 with all workers occupied",
                7,
                apply=target != current,
                emergency=target != current,
            )

        if pressure:
            self.state = AutoscaleState.PRESSURE
            self.pressure_count += 1
            self.calm_since = None
            self.last_pressure_at = now
            self.emergency_used = False
            target = current
            if (
                self.pressure_count >= self.config.pressure_confirmations
                and now - self.last_scale_at >= self.config.scale_up_cooldown_seconds
            ):
                target = self.config.clamp(current + 2)
                if target > current:
                    self.last_scale_at = now
                    self.pressure_count = 0
            return AutoscaleDecision(
                self.state,
                "workers",
                current,
                target,
                "Queue wait is high, worker utilization is above 80%, and backlog is rising",
                15,
                apply=target != current,
            )

        self.pressure_count = 0
        self.emergency_used = False
        calm = queue_peak <= 1 and occupancy < 0.5 and queue_wait < 100
        if now - self.last_pressure_at < self.config.recovery_seconds:
            self.state = AutoscaleState.RECOVERY
            self.calm_since = None
            return AutoscaleDecision(
                self.state,
                "healthy",
                current,
                current,
                "Capacity is stabilizing after recent pressure",
                30,
            )

        self.state = AutoscaleState.CALM
        if calm:
            if self.calm_since is None:
                self.calm_since = now
            if (
                current > self.config.min_workers
                and now - self.calm_since >= self.config.calm_seconds_before_downscale
            ):
                target = self.config.clamp(current - 1)
                self.calm_since = now
                return AutoscaleDecision(
                    self.state,
                    "healthy",
                    current,
                    target,
                    "Five minutes of low utilization and an empty queue",
                    60,
                    apply=True,
                )
        else:
            self.calm_since = None
        return AutoscaleDecision(
            self.state,
            "healthy",
            current,
            current,
            "Current capacity matches observed traffic",
            60,
        )


@dataclass
class WorkerSlot:
    worker_id: int
    task: asyncio.Task
    stop_event: asyncio.Event
    draining: bool = False


class WebhookWorkerManager:
    """Own live worker tasks and apply decisions without cancelling active work."""

    def __init__(
        self,
        worker_factory: Callable[[int, asyncio.Event], Awaitable[None]],
        snapshot_provider: Callable[[], dict],
        *,
        config: AutoscaleConfig | None = None,
        persist_decision: Callable[[dict], Awaitable[None]] | None = None,
        worker_is_active: Callable[[int], bool] | None = None,
    ):
        self.config = config or AutoscaleConfig.from_env()
        self.worker_factory = worker_factory
        self.snapshot_provider = snapshot_provider
        self.persist_decision = persist_decision
        self.worker_is_active = worker_is_active or (lambda _worker_id: False)
        self.engine = AutoscaleDecisionEngine(self.config)
        self.mode = "auto" if self.config.enabled else "off"
        self.observe_only = self.config.observe_only
        self.slots: dict[int, WorkerSlot] = {}
        self._next_worker_id = 1
        self._desired_workers = 0
        self._runner_task: asyncio.Task | None = None
        self._stopping = False
        self._last_decision: AutoscaleDecision | None = None
        self._next_analysis_at = 0.0
        self._timeline: list[dict] = []
        self.last_error: str | None = None

    @property
    def worker_count(self) -> int:
        return sum(1 for slot in self.slots.values() if not slot.draining and not slot.task.done())

    @property
    def tasks(self) -> list[asyncio.Task]:
        return [slot.task for slot in self.slots.values() if not slot.task.done()]

    async def start(self, initial_workers: int | None = None) -> None:
        target = self.config.clamp(initial_workers or self.config.initial_workers)
        await self.set_target(target, reason="startup")
        if self._runner_task is None or self._runner_task.done():
            self._runner_task = asyncio.create_task(self._run(), name="webhook-autoscaler")

    def _spawn(self) -> WorkerSlot:
        worker_id = self._next_worker_id
        self._next_worker_id += 1
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self.worker_factory(worker_id, stop_event),
            name=f"webhook-worker-{worker_id}",
        )
        slot = WorkerSlot(worker_id, task, stop_event)
        self.slots[worker_id] = slot

        def cleanup(_task: asyncio.Task) -> None:
            if self._stopping:
                return
            was_draining = slot.draining
            self.slots.pop(worker_id, None)
            exc = None
            if not _task.cancelled():
                try:
                    exc = _task.exception()
                except asyncio.CancelledError:
                    pass
            if not was_draining:
                if exc is not None:
                    logger.error("Webhook worker %d stopped unexpectedly: %s", worker_id, exc)
                else:
                    logger.warning("Webhook worker %d stopped unexpectedly", worker_id)
                while not self._stopping and self.worker_count < self._desired_workers:
                    self._spawn()

        task.add_done_callback(cleanup)
        return slot

    async def set_target(self, target_workers: int, *, reason: str) -> int:
        target = self.config.clamp(target_workers)
        self._desired_workers = target
        current = self.worker_count
        for _ in range(max(0, target - current)):
            self._spawn()
        remove_count = max(0, current - target)
        if remove_count:
            candidates = [
                slot for slot in sorted(self.slots.values(), key=lambda item: item.worker_id, reverse=True)
                if not slot.draining and not slot.task.done()
            ]
            for slot in candidates[:remove_count]:
                slot.draining = True
                slot.stop_event.set()
                if not self.worker_is_active(slot.worker_id):
                    slot.task.cancel()
        logger.info(
            "Webhook worker target=%d current=%d reason=%s observe_only=%s",
            target,
            self.worker_count,
            reason,
            self.observe_only,
        )
        return self.worker_count

    async def configure(
        self,
        *,
        mode: str | None = None,
        min_workers: int | None = None,
        max_workers: int | None = None,
        target_workers: int | None = None,
        observe_only: bool | None = None,
    ) -> dict:
        if min_workers is not None:
            self.config.min_workers = max(1, int(min_workers))
        if max_workers is not None:
            self.config.max_workers = max(self.config.min_workers, int(max_workers))
        if observe_only is not None:
            self.observe_only = bool(observe_only)
        if mode is not None:
            normalized = str(mode).lower()
            if normalized not in {"auto", "manual", "off"}:
                raise ValueError("mode must be auto, manual, or off")
            self.mode = normalized
        if target_workers is not None:
            self.mode = "manual" if mode is None else self.mode
            await self.set_target(int(target_workers), reason="manual dashboard change")
        elif self.worker_count < self.config.min_workers or self.worker_count > self.config.max_workers:
            await self.set_target(self.worker_count, reason="updated worker safety bounds")
        return self.status()

    async def _record(self, decision: AutoscaleDecision, applied_target: int) -> None:
        payload = {
            "state": decision.state.value,
            "bottleneck": decision.bottleneck,
            "workers_before": decision.current_workers,
            "workers_after": applied_target,
            "proposed_workers": decision.target_workers,
            "reason": decision.reason,
            "observe_only": self.observe_only,
            "next_analysis_seconds": decision.next_analysis_seconds,
            "metrics": self.snapshot_provider(),
        }
        if self.persist_decision is not None:
            result = self.persist_decision(payload)
            if inspect.isawaitable(result):
                await result

    async def evaluate_once(self) -> AutoscaleDecision:
        snapshot = self.snapshot_provider()
        decision = self.engine.evaluate(snapshot, self.worker_count)
        applied_target = self.worker_count
        if self.mode == "auto" and decision.apply and not self.observe_only:
            applied_target = await self.set_target(decision.target_workers, reason=decision.reason)
        changed = (
            self._last_decision is None
            or decision.state != self._last_decision.state
            or decision.bottleneck != self._last_decision.bottleneck
            or decision.target_workers != decision.current_workers
        )
        if changed:
            await self._record(decision, applied_target)
        self._last_decision = decision
        self._next_analysis_at = time.time() + decision.next_analysis_seconds
        self._timeline.append({
            "timestamp": time.time(),
            "workers": self.worker_count,
            "active": int((snapshot.get("workers") or {}).get("active") or 0),
            "queue": int((snapshot.get("queue") or {}).get("current") or 0),
            "queue_p95_ms": float((snapshot.get("queue") or {}).get("p95_wait_ms") or 0),
            "database_p95_ms": float((snapshot.get("database") or {}).get("p95_ms") or 0),
            "event_loop_p95_ms": float((snapshot.get("event_loop") or {}).get("p95_lag_ms") or 0),
        })
        self._timeline = self._timeline[-120:]
        return decision

    async def _run(self) -> None:
        delay = 1
        while not self._stopping:
            try:
                if self.mode == "auto":
                    decision = await self.evaluate_once()
                    delay = decision.next_analysis_seconds
                else:
                    delay = 30
                self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = str(exc)[:300]
                logger.exception("Webhook autoscaler failed; keeping current workers: %s", exc)
                delay = 60
            await asyncio.sleep(delay)

    def status(self) -> dict:
        decision = self._last_decision
        return {
            "mode": self.mode,
            "observe_only": self.observe_only,
            "enabled": self.mode != "off",
            "state": decision.state.value if decision else AutoscaleState.CALM.value,
            "bottleneck": decision.bottleneck if decision else "insufficient_data",
            "reason": decision.reason if decision else "Collecting initial metrics",
            "current_workers": self.worker_count,
            "desired_workers": self._desired_workers,
            "min_workers": self.config.min_workers,
            "max_workers": self.config.max_workers,
            "proposed_workers": decision.target_workers if decision else self.worker_count,
            "next_analysis_at": self._next_analysis_at,
            "last_error": self.last_error,
            "draining": sum(1 for slot in self.slots.values() if slot.draining and not slot.task.done()),
            "timeline": list(self._timeline),
        }

    async def stop(self) -> None:
        self._stopping = True
        if self._runner_task is not None:
            self._runner_task.cancel()
            await asyncio.gather(self._runner_task, return_exceptions=True)
        for slot in self.slots.values():
            slot.stop_event.set()
            slot.task.cancel()
        if self.slots:
            await asyncio.gather(*(slot.task for slot in self.slots.values()), return_exceptions=True)
