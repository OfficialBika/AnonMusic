import os
import unittest
from unittest.mock import patch

from config import Config


class ConfigTests(unittest.TestCase):
    def test_missing_env_names_are_reported_correctly(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
        with self.assertRaisesRegex(SystemExit, "SESSION"):
            cfg.check()

    def test_invalid_limits_fail_validation(self):
        env = {
            "API_ID": "123", "API_HASH": "hash", "BOT_TOKEN": "token",
            "MONGO_URL": "mongodb://localhost", "LOGGER_ID": "-100123",
            "OWNER_ID": "123", "SESSION": "session", "QUEUE_LIMIT": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = Config()
        with self.assertRaisesRegex(SystemExit, "QUEUE_LIMIT"):
            cfg.check()


if __name__ == "__main__":
    unittest.main()
