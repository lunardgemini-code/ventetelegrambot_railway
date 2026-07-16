import asyncio
import unittest

from services.runtime_metrics import (
    dependency_call,
    get_runtime_snapshot,
    reset_runtime_metrics_for_tests,
)
from services.webhook_autoscaler import (
    AutoscaleConfig,
    AutoscaleDecisionEngine,
    AutoscaleState,
    WebhookWorkerManager,
)


class Clock:
    def __init__(self, value=1000.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def snapshot(
    *,
    queue_wait=0,
    queue_current=0,
    queue_peak=0,
    queue_rising=False,
    utilization=0.1,
    samples=30,
    db_p95=50,
    db_errors=0,
    external_p95=100,
    external_calls=5,
    external_errors=0,
    external_timeouts=0,
    user_backlog=0,
    user_share=0,
    loop_p95=5,
    loop_max=10,
    memory=100,
):
    return {
        "workers": {"utilization_1m": utilization, "active": 0},
        "queue": {
            "p95_wait_ms": queue_wait,
            "current": queue_current,
            "peak_5m": queue_peak,
            "rising": queue_rising,
            "max_user_backlog": user_backlog,
            "largest_user_share": user_share,
        },
        "traffic": {"processed_5m": samples},
        "database": {
            "p95_ms": db_p95,
            "connection_errors": db_errors,
            "write_serialization": {"timeouts": 0, "p95_wait_ms": 0},
        },
        "external_apis": {
            "p95_ms": external_p95,
            "calls": external_calls,
            "errors": external_errors,
            "timeouts": external_timeouts,
        },
        "event_loop": {"p95_lag_ms": loop_p95, "max_lag_ms": loop_max},
        "memory": {"rss_mb": memory},
    }


class AutoscaleDecisionTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.config = AutoscaleConfig(
            enabled=True,
            observe_only=False,
            min_workers=8,
            max_workers=20,
            initial_workers=8,
            calm_seconds_before_downscale=300,
            pressure_confirmations=2,
            scale_up_cooldown_seconds=15,
            recovery_seconds=120,
        )
        self.engine = AutoscaleDecisionEngine(self.config, clock=self.clock)

    def test_normal_growth_requires_consecutive_pressure(self):
        metrics = snapshot(
            queue_wait=700,
            queue_current=12,
            queue_peak=14,
            queue_rising=True,
            utilization=0.9,
        )
        first = self.engine.evaluate(metrics, 8)
        self.clock.advance(15)
        second = self.engine.evaluate(metrics, 8)
        self.assertEqual(first.target_workers, 8)
        self.assertEqual(second.target_workers, 10)
        self.assertEqual(second.state, AutoscaleState.PRESSURE)

    def test_critical_growth_happens_only_once_before_observation(self):
        metrics = snapshot(
            queue_wait=1200,
            queue_current=51,
            queue_peak=60,
            queue_rising=True,
            utilization=1.0,
        )
        first = self.engine.evaluate(metrics, 8)
        self.clock.advance(7)
        second = self.engine.evaluate(metrics, 12)
        self.assertEqual(first.target_workers, 12)
        self.assertTrue(first.emergency)
        self.assertEqual(second.target_workers, 12)

    def test_database_external_loop_memory_and_single_user_block_growth(self):
        cases = [
            (snapshot(db_p95=900), "database"),
            (snapshot(external_p95=4000), "external_api"),
            (snapshot(loop_p95=300), "event_loop"),
            (snapshot(memory=500), "memory"),
            (snapshot(user_backlog=8, user_share=0.8), "single_user_backlog"),
        ]
        for metrics, expected in cases:
            with self.subTest(expected=expected):
                engine = AutoscaleDecisionEngine(self.config, clock=self.clock)
                decision = engine.evaluate(metrics, 8)
                self.assertEqual(decision.state, AutoscaleState.BOTTLENECK)
                self.assertEqual(decision.bottleneck, expected)
                self.assertEqual(decision.target_workers, 8)

    def test_downscale_only_after_five_minutes_of_calm(self):
        calm = snapshot(queue_peak=0, utilization=0.2)
        first = self.engine.evaluate(calm, 12)
        self.clock.advance(299)
        second = self.engine.evaluate(calm, 12)
        self.clock.advance(2)
        third = self.engine.evaluate(calm, 12)
        self.assertEqual(first.target_workers, 12)
        self.assertEqual(second.target_workers, 12)
        self.assertEqual(third.target_workers, 11)

    def test_minimum_and_maximum_are_never_crossed(self):
        critical = snapshot(queue_current=80, queue_peak=90, queue_rising=True, utilization=1)
        self.assertEqual(self.engine.evaluate(critical, 19).target_workers, 20)
        calm = snapshot(queue_peak=0, utilization=0.1)
        engine = AutoscaleDecisionEngine(self.config, clock=self.clock)
        engine.evaluate(calm, 8)
        self.clock.advance(301)
        self.assertEqual(engine.evaluate(calm, 8).target_workers, 8)


class WorkerManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_observation_records_proposal_without_scaling(self):
        metrics = snapshot(
            queue_wait=700,
            queue_current=12,
            queue_peak=14,
            queue_rising=True,
            utilization=0.9,
        )
        persisted = []

        async def worker(_worker_id, stop_event):
            await stop_event.wait()

        config = AutoscaleConfig(
            observe_only=True,
            min_workers=8,
            max_workers=12,
            initial_workers=8,
            pressure_confirmations=1,
            scale_up_cooldown_seconds=1,
        )
        manager = WebhookWorkerManager(
            worker,
            lambda: metrics,
            config=config,
            persist_decision=lambda item: _append_async(persisted, item),
        )
        manager.mode = "off"
        await manager.start(8)
        manager.mode = "auto"
        manager.engine.last_scale_at = 0
        try:
            decision = await manager.evaluate_once()
            self.assertEqual(decision.target_workers, 10)
            self.assertEqual(manager.worker_count, 8)
            self.assertTrue(persisted[-1]["observe_only"])
        finally:
            await manager.stop()

    async def test_active_worker_is_drained_without_cancellation(self):
        active = set()
        releases = {}

        async def worker(worker_id, stop_event):
            release = releases.setdefault(worker_id, asyncio.Event())
            active.add(worker_id)
            await release.wait()
            active.discard(worker_id)
            await stop_event.wait()

        config = AutoscaleConfig(min_workers=1, max_workers=3, initial_workers=2)
        manager = WebhookWorkerManager(
            worker,
            lambda: snapshot(),
            config=config,
            worker_is_active=lambda worker_id: worker_id in active,
        )
        manager.mode = "off"
        await manager.start(2)
        try:
            await asyncio.sleep(0)
            drained_id = max(manager.slots)
            await manager.set_target(1, reason="test drain")
            self.assertFalse(manager.slots[drained_id].task.done())
            self.assertTrue(manager.slots[drained_id].draining)
            releases[drained_id].set()
            await asyncio.wait_for(manager.slots[drained_id].task, timeout=1)
            self.assertEqual(manager.worker_count, 1)
        finally:
            for release in releases.values():
                release.set()
            await manager.stop()

    async def test_manual_target_respects_bounds(self):
        async def worker(_worker_id, stop_event):
            await stop_event.wait()

        manager = WebhookWorkerManager(
            worker,
            lambda: snapshot(),
            config=AutoscaleConfig(min_workers=2, max_workers=4, initial_workers=2),
        )
        manager.mode = "off"
        await manager.start(2)
        try:
            await manager.configure(mode="manual", target_workers=99)
            self.assertEqual(manager.worker_count, 4)
            await manager.configure(target_workers=1)
            self.assertEqual(manager.worker_count, 2)
        finally:
            await manager.stop()

    async def test_unexpected_worker_exit_is_replaced_at_fixed_target(self):
        starts = []
        first_release = asyncio.Event()

        async def worker(worker_id, stop_event):
            starts.append(worker_id)
            if len(starts) == 1:
                await first_release.wait()
                return
            await stop_event.wait()

        manager = WebhookWorkerManager(
            worker,
            lambda: snapshot(),
            config=AutoscaleConfig(min_workers=1, max_workers=3, initial_workers=1),
        )
        manager.mode = "off"
        await manager.start(1)
        try:
            first_release.set()
            for _ in range(20):
                if len(starts) >= 2:
                    break
                await asyncio.sleep(0.01)
            self.assertGreaterEqual(len(starts), 2)
            self.assertEqual(manager.worker_count, 1)
        finally:
            await manager.stop()


async def _append_async(target, value):
    target.append(value)


class RuntimeMetricTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_runtime_metrics_for_tests()

    async def test_external_calls_are_grouped_without_payloads(self):
        async with dependency_call("nowpayments", circuit_breaker=False):
            await asyncio.sleep(0)
        with self.assertRaises(TimeoutError):
            async with dependency_call("binance", circuit_breaker=False):
                raise TimeoutError("test")
        metrics = get_runtime_snapshot()
        self.assertEqual(metrics["external_apis"]["calls"], 2)
        self.assertEqual(metrics["external_apis"]["errors"], 1)
        self.assertEqual(metrics["external_apis"]["timeouts"], 1)
        self.assertEqual(
            {item["name"] for item in metrics["external_apis"]["dependencies"]},
            {"nowpayments", "binance"},
        )


if __name__ == "__main__":
    unittest.main()
