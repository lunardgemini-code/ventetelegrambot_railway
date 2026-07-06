# database/db.py — Connexion et initialisation de la base de données
# Supporte Turso (libSQL cloud) et SQLite local (fallback)

import os
import sqlite3
import asyncio

# ── Turso config ──
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")


# ══════════════════════════════════════════════
#  Async wrappers pour libsql (sync → async)
# ══════════════════════════════════════════════

class _DictRow(dict):
    """A dict subclass that also supports index-based access like sqlite3.Row."""

    def __init__(self, keys, values):
        super().__init__(zip(keys, values))
        self._keys = keys
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)

    def keys(self):
        return self._keys


class _AsyncCursor:
    """Wraps a sync libsql cursor to support await cursor.fetchall() etc."""

    def __init__(self, cursor):
        self._cursor = cursor
        # Get column names from description (may be None for non-SELECT)
        try:
            desc = cursor.description
            self._columns = [d[0] for d in desc] if desc else []
        except (AttributeError, TypeError):
            self._columns = []

    async def fetchall(self):
        rows = await asyncio.to_thread(self._cursor.fetchall)
        if not self._columns:
            return rows
        return [_DictRow(self._columns, row) for row in rows]

    async def fetchone(self):
        row = await asyncio.to_thread(self._cursor.fetchone)
        if row is None or not self._columns:
            return row
        return _DictRow(self._columns, row)

    @property
    def lastrowid(self):
        try:
            return self._cursor.lastrowid
        except (AttributeError, Exception):
            return None

    @property
    def rowcount(self):
        try:
            return self._cursor.rowcount
        except (AttributeError, Exception):
            return -1


class _AsyncDB:
    """Wraps a sync libsql connection to support await db.execute() etc."""

    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql, params=None):
        if params:
            if isinstance(params, list):
                params = tuple(params)
            cursor = await asyncio.to_thread(self._conn.execute, sql, params)
        else:
            cursor = await asyncio.to_thread(self._conn.execute, sql)
        return _AsyncCursor(cursor)

    async def executemany(self, sql, params_list):
        await asyncio.to_thread(self._conn.executemany, sql, params_list)

    async def executescript(self, sql):
        await asyncio.to_thread(self._conn.executescript, sql)

    async def commit(self):
        await asyncio.to_thread(self._conn.commit)

    async def rollback(self):
        await asyncio.to_thread(self._conn.rollback)

    async def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ══════════════════════════════════════════════
#  Connection Pooling for Turso
# ══════════════════════════════════════════════

_libsql_pool = []
_pool_lock = None

def get_pool_lock():
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


class _PooledAsyncDB(_AsyncDB):
    """Wraps a pooled libsql connection to return it to the pool on close."""

    def __init__(self, conn):
        super().__init__(conn)
        self.has_error = False

    @staticmethod
    def _is_connection_error(exc):
        """Returns True only for connection-level errors (broken pipe, stream lost, etc.)."""
        if isinstance(exc, (OSError, ConnectionError)):
            return True
        msg = str(exc).lower()
        return any(kw in msg for kw in ("stream", "hrana", "connection", "broken pipe", "timed out"))

    async def execute(self, sql, params=None):
        try:
            return await super().execute(sql, params)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
            raise

    async def executemany(self, sql, params_list):
        try:
            await super().executemany(sql, params_list)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
            raise

    async def executescript(self, sql):
        try:
            await super().executescript(sql)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
            raise

    async def commit(self):
        try:
            await super().commit()
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
            raise

    async def rollback(self):
        try:
            await super().rollback()
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
            raise

    async def close(self):
        """Returns the connection to the pool or closes it if an error occurred."""
        if self.has_error:
            try:
                await asyncio.to_thread(self._conn.close)
            except Exception:
                pass
            return

        async with get_pool_lock():
            if len(_libsql_pool) < 10:
                _libsql_pool.append(self._conn)
            else:
                try:
                    await asyncio.to_thread(self._conn.close)
                except Exception:
                    pass


# ══════════════════════════════════════════════
#  get_db() — returns async-compatible connection
# ══════════════════════════════════════════════

async def get_db():
    """Ouvre et retourne une connexion à la base de données.

    Si TURSO_DATABASE_URL est défini, connecte à Turso (libSQL cloud).
    Sinon, utilise un fichier SQLite local (fallback pour le dev).
    """
    if TURSO_URL:
        import libsql_experimental as libsql
        async with get_pool_lock():
            if _libsql_pool:
                conn = _libsql_pool.pop()
            else:
                conn = await asyncio.to_thread(libsql.connect, TURSO_URL, auth_token=TURSO_TOKEN)
        wrapper = _PooledAsyncDB(conn)
        try:
            await wrapper.execute("SELECT 1")
            await wrapper.execute("PRAGMA foreign_keys = ON")
        except Exception:
            # Stale connection from pool failed — close it and establish a fresh connection asynchronously
            try:
                await asyncio.to_thread(conn.close)
            except Exception:
                pass
            conn = await asyncio.to_thread(libsql.connect, TURSO_URL, auth_token=TURSO_TOKEN)
            wrapper = _PooledAsyncDB(conn)
            try:
                await wrapper.execute("PRAGMA foreign_keys = ON")
            except Exception:
                pass
        return wrapper
    else:
        import aiosqlite
        db = await aiosqlite.connect(os.environ.get("DB_PATH", "bot_data.db"))
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        return db


# ══════════════════════════════════════════════
#  init_db() — Crée les tables
# ══════════════════════════════════════════════

async def init_db() -> None:
    """Crée toutes les tables nécessaires si elles n'existent pas encore."""
    db = await get_db()
    try:
        tables = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                language TEXT,
                total_spent REAL DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '📂',
                description TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                description_fr TEXT DEFAULT '',
                description_ar TEXT DEFAULT '',
                description_zh TEXT DEFAULT '',
                price_usd REAL NOT NULL,
                warranty_days INTEGER DEFAULT 0,
                emoji TEXT DEFAULT '📦',
                custom_emoji_id TEXT DEFAULT NULL,
                image_url TEXT DEFAULT NULL,
                delivery_type TEXT DEFAULT 'stock',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                binance_account_id INTEGER DEFAULT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )""",
            """CREATE TABLE IF NOT EXISTS price_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                min_qty INTEGER NOT NULL,
                max_qty INTEGER NOT NULL,
                price_usd REAL NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                account_data TEXT NOT NULL,
                is_sold INTEGER DEFAULT 0,
                sold_to_order_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sold_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""",
            """CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                stock_item_id INTEGER,
                amount_usd REAL NOT NULL,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'PENDING',
                merchant_trade_no TEXT UNIQUE,
                binance_order_id TEXT,
                payment_method TEXT DEFAULT 'binance',
                promo_code_id INTEGER,
                promo_discount REAL DEFAULT 0.0,
                activation_identifier TEXT,
                activation_status TEXT DEFAULT NULL,
                activation_requested_at TIMESTAMP,
                activated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""",
            """CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                admin_reply TEXT,
                status TEXT DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_type TEXT DEFAULT 'percent',
                discount_value REAL NOT NULL,
                max_uses INTEGER DEFAULT 0,
                max_uses_per_user INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                applicable_product_ids TEXT DEFAULT NULL,
                max_qty_per_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS promo_code_usages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promo_code_id INTEGER NOT NULL,
                user_telegram_id INTEGER NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(promo_code_id, user_telegram_id)
            )""",
            """CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS used_binance_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                order_id INTEGER,
                user_telegram_id INTEGER,
                amount REAL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS used_bep20_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE NOT NULL,
                order_id INTEGER,
                user_telegram_id INTEGER,
                amount REAL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS binance_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                uid TEXT NOT NULL,
                api_key TEXT DEFAULT '',
                api_secret TEXT DEFAULT '',
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS used_trc20_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE NOT NULL,
                order_id INTEGER,
                user_telegram_id INTEGER,
                amount REAL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS reseller_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                name TEXT DEFAULT '',
                key_prefix TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
            )""",
            """CREATE TABLE IF NOT EXISTS reseller_order_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER UNIQUE NOT NULL,
                reseller_user_telegram_id INTEGER NOT NULL,
                customer_reference TEXT DEFAULT '',
                idempotency_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                UNIQUE(reseller_user_telegram_id, idempotency_key)
            )""",
        ]

        for sql in tables:
            await db.execute(sql)
        await db.commit()

        migrations = [
            "ALTER TABLE users ADD COLUMN wallet_balance REAL DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN promo_code_id INTEGER",
            "ALTER TABLE orders ADD COLUMN promo_discount REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER",
            "ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN referral_commission_paid REAL DEFAULT 0",
            "CREATE INDEX IF NOT EXISTS idx_stock_product_sold ON stock_items(product_id, is_sold)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_used_bep20_tx ON used_bep20_transactions(tx_hash)",
            "CREATE INDEX IF NOT EXISTS idx_used_trc20_tx ON used_trc20_transactions(tx_hash)",
            "CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)",
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_price_tiers_product ON price_tiers(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_wallet_tx_user ON wallet_transactions(user_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_stock_sold_product ON stock_items(is_sold, product_id)",
            "CREATE INDEX IF NOT EXISTS idx_stock_order ON stock_items(sold_to_order_id)",
            "CREATE INDEX IF NOT EXISTS idx_stock_product_sold_added ON stock_items(product_id, is_sold, added_at)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_orders_product_status ON orders(product_id, status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_wallet_tx_type_created ON wallet_transactions(type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status, created_at)",
            "ALTER TABLE categories ADD COLUMN is_deleted INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN is_deleted INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN binance_account_id INTEGER DEFAULT NULL",
            "CREATE TABLE IF NOT EXISTS binance_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, uid TEXT NOT NULL, api_key TEXT DEFAULT '', api_secret TEXT DEFAULT '', is_default INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "UPDATE orders SET binance_order_id = (SELECT transaction_id FROM used_binance_transactions WHERE used_binance_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_binance_transactions WHERE order_id IS NOT NULL)",
            "UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_bep20_transactions WHERE used_bep20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_bep20_transactions WHERE order_id IS NOT NULL)",
            "UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_trc20_transactions WHERE used_trc20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_trc20_transactions WHERE order_id IS NOT NULL)",
            "ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT NULL",
        "INSERT OR IGNORE INTO settings (key, value) SELECT 'finance_bot_balance_binance', value FROM settings WHERE key = 'finance_bot_balance'",
            "ALTER TABLE promo_codes ADD COLUMN max_uses_per_user INTEGER DEFAULT 0",
            "CREATE TABLE IF NOT EXISTS promo_code_usages (id INTEGER PRIMARY KEY AUTOINCREMENT, promo_code_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, usage_count INTEGER DEFAULT 0, last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(promo_code_id, user_telegram_id))",
            "ALTER TABLE promo_codes ADD COLUMN applicable_product_ids TEXT DEFAULT NULL",
            "ALTER TABLE promo_codes ADD COLUMN max_qty_per_order INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN description_fr TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_ar TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_zh TEXT DEFAULT ''",
            "ALTER TABLE wallet_transactions ADD COLUMN tx_hash TEXT DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN delivery_type TEXT DEFAULT 'stock'",
            "ALTER TABLE orders ADD COLUMN activation_identifier TEXT",
            "ALTER TABLE orders ADD COLUMN activation_status TEXT DEFAULT NULL",
            "ALTER TABLE orders ADD COLUMN activation_requested_at TIMESTAMP",
            "ALTER TABLE orders ADD COLUMN activated_at TIMESTAMP",
            "ALTER TABLE products ADD COLUMN activation_message TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN activation_message_fr TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN activation_message_ar TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN activation_message_zh TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_fr TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_ar TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_zh TEXT DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS idx_orders_activation_status ON orders(activation_status, status)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_keys_user ON reseller_api_keys(user_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_keys_prefix ON reseller_api_keys(key_prefix)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_orders_user ON reseller_order_links(reseller_user_telegram_id, created_at)",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception as e:
                print(f"Migration skip/error for '{sql}': {e}")
        await db.commit()

    finally:
        await db.close()
