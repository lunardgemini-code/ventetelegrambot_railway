import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from database import db


class TursoDbRetryTests(unittest.IsolatedAsyncioTestCase):
    def test_is_turso_connection_reset_error_detection(self):
        exc1 = ValueError("Hrana: http error: error trying to connect: Connection reset by peer (os error 104)")
        exc2 = RuntimeError("connection closed by server")
        exc3 = ValueError("Syntax error in query")

        self.assertTrue(db._is_turso_connection_reset_error(exc1))
        self.assertTrue(db._is_turso_connection_reset_error(exc2))
        self.assertFalse(db._is_turso_connection_reset_error(exc3))

    async def test_run_turso_call_retries_on_connection_reset(self):
        calls = 0

        def flaky_func():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("Connection reset by peer (os error 104)")
            return "success"

        result = await db._run_turso_call(flaky_func, timeout=2.0)
        self.assertEqual(result, "success")
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
