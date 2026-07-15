import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.process_supervisor import SupervisorConfig, supervise


class ProcessSupervisorTests(unittest.TestCase):
    def test_config_clamps_invalid_environment_values(self):
        with patch.dict(
            os.environ,
            {
                "PROCESS_SUPERVISOR_RESTART_DELAY_SECONDS": "-1",
                "PROCESS_SUPERVISOR_MAX_RESTARTS": "0",
                "PROCESS_SUPERVISOR_RESTART_WINDOW_SECONDS": "5",
            },
            clear=False,
        ):
            config = SupervisorConfig.from_env()

        self.assertEqual(config.restart_delay_seconds, 0)
        self.assertEqual(config.max_restarts, 1)
        self.assertEqual(config.restart_window_seconds, 30)

    def test_unexpected_bot_exit_is_restarted(self):
        first = SimpleNamespace(pid=101, wait=Mock(return_value=-9))
        second = SimpleNamespace(pid=102, wait=Mock(return_value=1))
        popen = Mock(side_effect=[first, second])
        sleeper = Mock()
        messages = []

        result = supervise(
            SupervisorConfig(
                restart_delay_seconds=2,
                max_restarts=1,
                restart_window_seconds=600,
            ),
            popen_factory=popen,
            sleeper=sleeper,
            clock=Mock(side_effect=[100, 101]),
            install_signal_handlers=False,
            log=messages.append,
        )

        self.assertEqual(result, 1)
        self.assertEqual(popen.call_count, 2)
        sleeper.assert_called_once_with(2)
        self.assertTrue(any("code -9" in message for message in messages))
        self.assertTrue(any("budget exhausted" in message for message in messages))

    def test_restart_budget_resets_after_window(self):
        processes = [
            SimpleNamespace(pid=201, wait=Mock(return_value=1)),
            SimpleNamespace(pid=202, wait=Mock(return_value=1)),
            SimpleNamespace(pid=203, wait=Mock(return_value=2)),
        ]
        popen = Mock(side_effect=processes)

        result = supervise(
            SupervisorConfig(
                restart_delay_seconds=0,
                max_restarts=1,
                restart_window_seconds=30,
            ),
            popen_factory=popen,
            sleeper=lambda _seconds: None,
            clock=Mock(side_effect=[100, 200, 201]),
            install_signal_handlers=False,
            log=lambda _message: None,
        )

        self.assertEqual(result, 2)
        self.assertEqual(popen.call_count, 3)


if __name__ == "__main__":
    unittest.main()
