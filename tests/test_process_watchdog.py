import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.process_watchdog import (
    WatchdogConfig,
    monitor_parent,
    probe_liveness,
    start_process_watchdog,
    stop_process_watchdog,
)


class ProcessWatchdogTests(unittest.TestCase):
    @patch("services.process_watchdog.HTTPConnection")
    def test_liveness_probe_uses_direct_local_connection(self, connection_class):
        response = SimpleNamespace(status=200, read=Mock(return_value=b'{"status":"ok"}'))
        connection = connection_class.return_value
        connection.getresponse.return_value = response

        healthy = probe_liveness("http://127.0.0.1:8000/health/live", 3)

        self.assertTrue(healthy)
        connection_class.assert_called_once_with("127.0.0.1", 8000, timeout=3)
        connection.request.assert_called_once_with(
            "GET",
            "/health/live",
            headers={"User-Agent": "VenteBot-Process-Watchdog/1.0"},
        )
        connection.close.assert_called_once_with()

    def test_config_clamps_unsafe_values(self):
        with patch.dict(
            os.environ,
            {
                "PROCESS_WATCHDOG_ENABLED": "true",
                "PROCESS_WATCHDOG_STARTUP_GRACE_SECONDS": "-5",
                "PROCESS_WATCHDOG_INTERVAL_SECONDS": "0",
                "PROCESS_WATCHDOG_TIMEOUT_SECONDS": "0",
                "PROCESS_WATCHDOG_FAILURE_THRESHOLD": "1",
                "PROCESS_WATCHDOG_DIAGNOSTIC_DELAY_SECONDS": "-1",
            },
            clear=False,
        ):
            config = WatchdogConfig.from_env()

        self.assertTrue(config.enabled)
        self.assertEqual(config.startup_grace_seconds, 0)
        self.assertEqual(config.interval_seconds, 1)
        self.assertEqual(config.request_timeout_seconds, 0.5)
        self.assertEqual(config.failure_threshold, 2)
        self.assertEqual(config.diagnostic_delay_seconds, 0)

    def test_monitor_resets_failures_before_reaching_threshold(self):
        probes = iter([False, False, True, False, False, True])
        alive_checks = 0
        signals = []

        def is_alive(_pid):
            nonlocal alive_checks
            alive_checks += 1
            return alive_checks <= 7

        result = monitor_parent(
            42,
            8000,
            WatchdogConfig(
                startup_grace_seconds=0,
                interval_seconds=1,
                request_timeout_seconds=1,
                failure_threshold=3,
                diagnostic_delay_seconds=0,
            ),
            probe=lambda _url, _timeout: next(probes),
            is_alive=is_alive,
            send_signal=lambda pid, sig: signals.append((pid, sig)),
            sleeper=lambda _seconds: None,
            log=lambda _message: None,
            diagnostic_signal=100,
            kill_signal=200,
        )

        self.assertEqual(result, 0)
        self.assertEqual(signals, [])

    def test_monitor_dumps_threads_then_kills_after_threshold(self):
        signals = []
        result = monitor_parent(
            42,
            8000,
            WatchdogConfig(
                startup_grace_seconds=0,
                interval_seconds=1,
                request_timeout_seconds=1,
                failure_threshold=3,
                diagnostic_delay_seconds=0,
            ),
            probe=lambda _url, _timeout: False,
            is_alive=lambda _pid: True,
            send_signal=lambda pid, sig: signals.append((pid, sig)),
            sleeper=lambda _seconds: None,
            log=lambda _message: None,
            diagnostic_signal=100,
            kill_signal=200,
        )

        self.assertEqual(result, 2)
        self.assertEqual(signals, [(42, 100), (42, 200)])

    def test_start_and_stop_watchdog_manage_child_process(self):
        process = SimpleNamespace(
            pid=99,
            poll=Mock(return_value=None),
            terminate=Mock(),
            wait=Mock(return_value=0),
            kill=Mock(),
        )
        popen = Mock(return_value=process)
        config = WatchdogConfig(startup_grace_seconds=5)

        started = start_process_watchdog(42, 8000, config, popen_factory=popen)
        stop_process_watchdog(started)

        self.assertIs(started, process)
        command = popen.call_args.args[0]
        self.assertIn("--parent-pid", command)
        self.assertIn("42", command)
        self.assertIn("--port", command)
        self.assertIn("8000", command)
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once()
        process.kill.assert_not_called()

    def test_disabled_watchdog_does_not_spawn(self):
        popen = Mock()
        started = start_process_watchdog(
            42,
            8000,
            WatchdogConfig(enabled=False),
            popen_factory=popen,
        )

        self.assertIsNone(started)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
