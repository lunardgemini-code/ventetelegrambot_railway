import os
import tempfile
import unittest

from cryptography.fernet import Fernet

from database import db as db_module
from database import models
from database.db import get_db, init_db


class SecretStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        self.previous_keys = os.environ.pop("CREDENTIAL_ENCRYPTION_KEYS", None)
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "secret-storage.db")
        os.environ["CREDENTIAL_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models._clear_binance_account_cache()
        await init_db()

    async def asyncTearDown(self):
        models._clear_binance_account_cache()
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        if self.previous_key is None:
            os.environ.pop("CREDENTIAL_ENCRYPTION_KEY", None)
        else:
            os.environ["CREDENTIAL_ENCRYPTION_KEY"] = self.previous_key
        if self.previous_keys is not None:
            os.environ["CREDENTIAL_ENCRYPTION_KEYS"] = self.previous_keys
        self.temp_dir.cleanup()

    async def _raw_credentials(self, account_id: int):
        db = await get_db()
        try:
            return await (await db.execute(
                "SELECT api_key, api_secret FROM binance_accounts WHERE id = ?",
                (account_id,),
            )).fetchone()
        finally:
            await db.close()

    async def test_new_binance_credentials_are_encrypted_at_rest(self):
        account_id = await models.add_binance_account(
            "Primary", "123456", "binance-key", "binance-secret", 1
        )
        stored = await self._raw_credentials(account_id)
        self.assertTrue(str(stored["api_key"]).startswith("enc:v1:"))
        self.assertTrue(str(stored["api_secret"]).startswith("enc:v1:"))
        self.assertNotIn("binance-key", str(stored["api_key"]))

        account = await models.get_binance_account(account_id)
        self.assertEqual(account["api_key"], "binance-key")
        self.assertEqual(account["api_secret"], "binance-secret")

    async def test_legacy_plaintext_credentials_are_migrated_on_read(self):
        db = await get_db()
        try:
            cursor = await db.execute(
                "INSERT INTO binance_accounts (label, uid, api_key, api_secret) VALUES (?, ?, ?, ?)",
                ("Legacy", "654321", "legacy-key", "legacy-secret"),
            )
            await db.commit()
            account_id = int(cursor.lastrowid)
        finally:
            await db.close()

        account = await models.get_binance_account(account_id)
        stored = await self._raw_credentials(account_id)
        self.assertEqual(account["api_key"], "legacy-key")
        self.assertEqual(account["api_secret"], "legacy-secret")
        self.assertTrue(str(stored["api_key"]).startswith("enc:v1:"))
        self.assertTrue(str(stored["api_secret"]).startswith("enc:v1:"))


if __name__ == "__main__":
    unittest.main()
