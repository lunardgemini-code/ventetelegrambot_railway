import os
import unittest
from unittest.mock import patch

from services.webhook_autoscaler import AutoscaleConfig


class WebhookAutoscaleDefaultTests(unittest.TestCase):
    def test_idle_floor_is_six_but_startup_capacity_remains_eight(self):
        with patch.dict(
            os.environ,
            {
                "WEBHOOK_WORKERS_MIN": "6",
                "WEBHOOK_WORKERS_INITIAL": "8",
                "WEBHOOK_WORKERS_MAX": "20",
            },
            clear=False,
        ):
            config = AutoscaleConfig.from_env()

        self.assertEqual(config.min_workers, 6)
        self.assertEqual(config.initial_workers, 8)
        self.assertEqual(config.max_workers, 20)

    def test_environment_can_raise_the_production_floor(self):
        with patch.dict(
            os.environ,
            {
                "WEBHOOK_WORKERS_MIN": "10",
                "WEBHOOK_WORKERS_INITIAL": "8",
                "WEBHOOK_WORKERS_MAX": "20",
            },
            clear=False,
        ):
            config = AutoscaleConfig.from_env()

        self.assertEqual(config.min_workers, 10)
        self.assertGreaterEqual(config.initial_workers, 10)


if __name__ == "__main__":
    unittest.main()
