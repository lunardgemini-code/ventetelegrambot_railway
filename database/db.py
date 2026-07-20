# database/db.py — Connexion et initialisation de la base de données
# Supporte Turso (libSQL cloud) et SQLite local (fallback)

import os
import sqlite3
import asyncio
import logging
import time
from collections import Counter, deque

logger = logging.getLogger(__name__)

_DB_OPERATION_SAMPLES = deque(maxlen=5000)
_DB_CONNECTION_ERROR_TIMES = deque(maxlen=1000)
_DB_CONNECTION_EVENTS = deque(maxlen=5000)
_DB_WRITE_LOCK_SAMPLES = deque(maxlen=5000)
_DB_CONNECTION_STATS = {"fresh": 0, "pooled": 0, "discarded": 0}
_DB_WRITE_WAITERS = 0


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return min(maximum, max(minimum, int(os.environ.get(name, str(default)))))
    except (TypeError, ValueError):
        return default


def _record_db_operation(operation: str, started_at: float, success: bool) -> None:
    _DB_OPERATION_SAMPLES.append(
        (time.monotonic(), operation, max(0.0, time.monotonic() - started_at), success)
    )


def _connection_error_category(exc: Exception) -> str:
    message = str(exc).lower()
    if "stream not found" in message:
        return "stream_not_found"
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "broken pipe" in message:
        return "broken_pipe"
    if "hrana" in message:
        return "hrana"
    return "connection"


def _record_db_connection_error(exc: Exception, operation: str) -> None:
    _DB_CONNECTION_ERROR_TIMES.append(
        (time.monotonic(), _connection_error_category(exc), operation)
    )


def _record_connection_event(kind: str) -> None:
    _DB_CONNECTION_EVENTS.append((time.monotonic(), kind))


def _record_write_lock_wait(started_at: float, success: bool) -> None:
    _DB_WRITE_LOCK_SAMPLES.append(
        (time.monotonic(), max(0.0, time.monotonic() - started_at), success)
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[index]


def get_db_performance_snapshot(window_seconds: int = 300) -> dict:
    """Return in-process DB latency and connection health metrics."""
    now = time.monotonic()
    cutoff = now - max(10, int(window_seconds))
    samples = [sample for sample in _DB_OPERATION_SAMPLES if sample[0] >= cutoff]
    durations = [sample[2] for sample in samples]
    connection_errors = [event for event in _DB_CONNECTION_ERROR_TIMES if event[0] >= cutoff]
    connection_events = [event for event in _DB_CONNECTION_EVENTS if event[0] >= cutoff]
    write_lock_samples = [event for event in _DB_WRITE_LOCK_SAMPLES if event[0] >= cutoff]
    write_waits = [event[1] for event in write_lock_samples if event[2]]
    error_categories = Counter(event[1] for event in connection_errors)
    error_operations = Counter(event[2] for event in connection_errors)
    recent_connections = Counter(event[1] for event in connection_events)
    return {
        "operations": len(samples),
        "errors": sum(1 for sample in samples if not sample[3]),
        "connection_errors": len(connection_errors),
        "connection_error_categories": dict(error_categories),
        "connection_error_operations": dict(error_operations),
        "average_ms": round((sum(durations) / len(durations) * 1000) if durations else 0, 1),
        "p95_ms": round(_percentile(durations, 0.95) * 1000, 1),
        "slow_operations": sum(1 for duration in durations if duration >= 1.0),
        "connections": {
            "totals_since_start": dict(_DB_CONNECTION_STATS),
            "window": dict(recent_connections),
        },
        "write_serialization": {
            "locked": bool(_turso_writer_lock and _turso_writer_lock.locked()),
            "waiters": _DB_WRITE_WAITERS,
            "acquisitions": len(write_waits),
            "timeouts": sum(1 for event in write_lock_samples if not event[2]),
            "average_wait_ms": round(
                (sum(write_waits) / len(write_waits) * 1000) if write_waits else 0,
                1,
            ),
            "p95_wait_ms": round(_percentile(write_waits, 0.95) * 1000, 1),
        },
    }

# ── Turso config ──
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
_TURSO_OPERATION_TIMEOUT_SECONDS = _env_float(
    "TURSO_OPERATION_TIMEOUT_SECONDS", 15.0, 1.0
)
_TURSO_CLOSE_TIMEOUT_SECONDS = _env_float(
    "TURSO_CLOSE_TIMEOUT_SECONDS", 3.0, 0.5
)
_TURSO_WRITE_LOCK_TIMEOUT_SECONDS = _env_float(
    "TURSO_WRITE_LOCK_TIMEOUT_SECONDS", 15.0, 1.0
)


# ══════════════════════════════════════════════
#  Async wrappers pour libsql (sync → async)
# ══════════════════════════════════════════════

async def _run_turso_call(func, *args, timeout: float | None = None):
    """Run one native SDK call without letting an await hang indefinitely."""
    return await asyncio.wait_for(
        asyncio.to_thread(func, *args),
        timeout=timeout or _TURSO_OPERATION_TIMEOUT_SECONDS,
    )


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
        started_at = time.monotonic()
        try:
            rows = await _run_turso_call(self._cursor.fetchall)
            _record_db_operation("fetchall", started_at, True)
        except Exception:
            _record_db_operation("fetchall", started_at, False)
            raise
        if not self._columns:
            return rows
        return [_DictRow(self._columns, row) for row in rows]

    async def fetchone(self):
        started_at = time.monotonic()
        try:
            row = await _run_turso_call(self._cursor.fetchone)
            _record_db_operation("fetchone", started_at, True)
        except Exception:
            _record_db_operation("fetchone", started_at, False)
            raise
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
        started_at = time.monotonic()
        try:
            if params:
                if isinstance(params, list):
                    params = tuple(params)
                cursor = await _run_turso_call(self._conn.execute, sql, params)
            else:
                cursor = await _run_turso_call(self._conn.execute, sql)
            _record_db_operation("execute", started_at, True)
            return _AsyncCursor(cursor)
        except Exception:
            _record_db_operation("execute", started_at, False)
            raise

    async def executemany(self, sql, params_list):
        started_at = time.monotonic()
        try:
            await _run_turso_call(self._conn.executemany, sql, params_list)
            _record_db_operation("executemany", started_at, True)
        except Exception:
            _record_db_operation("executemany", started_at, False)
            raise

    async def executescript(self, sql):
        started_at = time.monotonic()
        try:
            await _run_turso_call(self._conn.executescript, sql)
            _record_db_operation("executescript", started_at, True)
        except Exception:
            _record_db_operation("executescript", started_at, False)
            raise

    async def commit(self):
        started_at = time.monotonic()
        try:
            await _run_turso_call(self._conn.commit)
            _record_db_operation("commit", started_at, True)
        except Exception:
            _record_db_operation("commit", started_at, False)
            raise

    async def rollback(self):
        started_at = time.monotonic()
        try:
            await _run_turso_call(self._conn.rollback)
            _record_db_operation("rollback", started_at, True)
        except Exception:
            _record_db_operation("rollback", started_at, False)
            raise

    async def close(self):
        try:
            await _run_turso_call(
                self._conn.close,
                timeout=_TURSO_CLOSE_TIMEOUT_SECONDS,
            )
        except Exception:
            pass


# ══════════════════════════════════════════════
#  Connection Pooling for Turso
# ══════════════════════════════════════════════

_libsql_pool = []
_pool_lock = None
_pool_lock_loop = None
_turso_connect_semaphore = None
_turso_connect_semaphore_loop = None
_turso_writer_lock = None
_turso_writer_lock_loop = None
_sqlite_wal_configured = False
_TURSO_POOL_MAX_IDLE_SECONDS = _env_float(
    "TURSO_POOL_MAX_IDLE_SECONDS", 5.0, 1.0
)
_TURSO_POOL_MAX_LIFETIME_SECONDS = _env_float(
    "TURSO_POOL_MAX_LIFETIME_SECONDS", 30.0, 5.0
)
_TURSO_CONNECT_CONCURRENCY = _env_int(
    "TURSO_CONNECT_CONCURRENCY", 4, 1, 10
)

def get_pool_lock():
    global _pool_lock, _pool_lock_loop
    loop = asyncio.get_running_loop()
    if _pool_lock is None or _pool_lock_loop is not loop:
        _pool_lock = asyncio.Lock()
        _pool_lock_loop = loop
    return _pool_lock


def get_turso_connect_semaphore():
    global _turso_connect_semaphore, _turso_connect_semaphore_loop
    loop = asyncio.get_running_loop()
    if _turso_connect_semaphore is None or _turso_connect_semaphore_loop is not loop:
        _turso_connect_semaphore = asyncio.Semaphore(_TURSO_CONNECT_CONCURRENCY)
        _turso_connect_semaphore_loop = loop
    return _turso_connect_semaphore


def get_turso_writer_lock():
    global _turso_writer_lock, _turso_writer_lock_loop
    loop = asyncio.get_running_loop()
    if _turso_writer_lock is None or _turso_writer_lock_loop is not loop:
        _turso_writer_lock = asyncio.Lock()
        _turso_writer_lock_loop = loop
    return _turso_writer_lock


def _sql_command(sql) -> str:
    normalized = str(sql or "").lstrip()
    while normalized.startswith("--"):
        _, separator, normalized = normalized.partition("\n")
        if not separator:
            return ""
        normalized = normalized.lstrip()
    while normalized.startswith("/*"):
        end = normalized.find("*/", 2)
        if end < 0:
            return ""
        normalized = normalized[end + 2 :].lstrip()
    return normalized.partition(" ")[0].partition("\n")[0].upper()


def _requires_turso_writer_lock(sql) -> bool:
    # The only WITH statement in this codebase is a read-only analytics query.
    return _sql_command(sql) not in {"", "SELECT", "WITH", "PRAGMA", "EXPLAIN"}


class _PooledAsyncDB(_AsyncDB):
    """Wraps a pooled libsql connection to return it to the pool on close."""

    def __init__(self, conn, *, created_at=None, return_to_pool=True):
        super().__init__(conn)
        self.has_error = False
        self.created_at = created_at if created_at is not None else time.monotonic()
        self.return_to_pool = return_to_pool
        self._write_lock = None
        self._write_lock_held = False
        self._closed = False

    async def _acquire_writer_lock(self) -> None:
        global _DB_WRITE_WAITERS
        if self._write_lock_held:
            return

        lock = get_turso_writer_lock()
        started_at = time.monotonic()
        _DB_WRITE_WAITERS += 1
        try:
            await asyncio.wait_for(
                lock.acquire(),
                timeout=_TURSO_WRITE_LOCK_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            _record_write_lock_wait(started_at, False)
            raise TimeoutError(
                "Timed out waiting for the Turso write queue"
            ) from exc
        else:
            _record_write_lock_wait(started_at, True)
            self._write_lock = lock
            self._write_lock_held = True
        finally:
            _DB_WRITE_WAITERS = max(0, _DB_WRITE_WAITERS - 1)

    def _release_writer_lock(self) -> None:
        if not self._write_lock_held:
            return
        lock = self._write_lock
        self._write_lock = None
        self._write_lock_held = False
        if lock is not None and lock.locked():
            lock.release()

    @staticmethod
    def _is_connection_error(exc):
        """Returns True only for connection-level errors (broken pipe, stream lost, etc.)."""
        if isinstance(exc, (OSError, ConnectionError)):
            return True
        msg = str(exc).lower()
        return any(kw in msg for kw in ("stream", "hrana", "connection", "broken pipe", "timed out"))

    @staticmethod
    def _execute_operation_name(sql) -> str:
        normalized = str(sql or "").strip().lower()
        if normalized.startswith("pragma foreign_keys"):
            return "pragma_foreign_keys"
        if normalized.startswith("select 1"):
            return "pool_validation"
        return "execute"

    async def execute(self, sql, params=None):
        command = _sql_command(sql)
        transaction_end = command in {"COMMIT", "END", "ROLLBACK"}
        if _requires_turso_writer_lock(sql) and not transaction_end:
            await self._acquire_writer_lock()
        try:
            return await super().execute(sql, params)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
                _record_db_connection_error(e, self._execute_operation_name(sql))
                self._release_writer_lock()
            raise
        finally:
            if transaction_end:
                self._release_writer_lock()

    async def executemany(self, sql, params_list):
        await self._acquire_writer_lock()
        try:
            await super().executemany(sql, params_list)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
                _record_db_connection_error(e, "executemany")
                self._release_writer_lock()
            raise

    async def executescript(self, sql):
        await self._acquire_writer_lock()
        try:
            await super().executescript(sql)
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
                _record_db_connection_error(e, "executescript")
                self._release_writer_lock()
            raise

    async def commit(self):
        try:
            await super().commit()
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
                _record_db_connection_error(e, "commit")
            raise
        finally:
            self._release_writer_lock()

    async def rollback(self):
        try:
            await super().rollback()
        except Exception as e:
            if self._is_connection_error(e):
                self.has_error = True
                _record_db_connection_error(e, "rollback")
            raise
        finally:
            self._release_writer_lock()

    async def close(self):
        """Returns the connection to the pool or closes it if an error occurred."""
        if self._closed:
            return
        self._closed = True

        if self._write_lock_held:
            # Never return an unfinished transaction to the pool.
            self.has_error = True
            try:
                await super().rollback()
            except Exception:
                pass
            finally:
                self._release_writer_lock()

        if (
            self.has_error
            or not self.return_to_pool
            or time.monotonic() - self.created_at > _TURSO_POOL_MAX_LIFETIME_SECONDS
        ):
            try:
                await _run_turso_call(
                    self._conn.close,
                    timeout=_TURSO_CLOSE_TIMEOUT_SECONDS,
                )
            except Exception:
                pass
            return

        close_overflow = False
        async with get_pool_lock():
            if len(_libsql_pool) < 10:
                _libsql_pool.append((self._conn, time.monotonic(), self.created_at))
            else:
                close_overflow = True
        if close_overflow:
            try:
                await _run_turso_call(
                    self._conn.close,
                    timeout=_TURSO_CLOSE_TIMEOUT_SECONDS,
                )
            except Exception:
                pass

# ══════════════════════════════════════════════
#  get_db() — returns async-compatible connection
# ══════════════════════════════════════════════

def is_transient_db_connection_error(exc: Exception) -> bool:
    """Return whether retrying on a fresh Turso connection is appropriate."""
    return _PooledAsyncDB._is_connection_error(exc)


async def _take_pooled_turso_connection():
    """Pop one live pooled connection without awaiting I/O under the pool lock."""
    expired_connections = []
    selected_connection = None
    selected_created_at = None
    now = time.monotonic()
    async with get_pool_lock():
        while _libsql_pool:
            pooled_entry = _libsql_pool.pop()
            if isinstance(pooled_entry, tuple):
                if len(pooled_entry) == 3:
                    candidate, returned_at, created_at = pooled_entry
                else:
                    candidate, returned_at = pooled_entry
                    created_at = returned_at
                if (
                    now - returned_at <= _TURSO_POOL_MAX_IDLE_SECONDS
                    and now - created_at <= _TURSO_POOL_MAX_LIFETIME_SECONDS
                ):
                    selected_connection = candidate
                    selected_created_at = created_at
                    break
                expired_connections.append(candidate)
            else:
                # Compatibility with connections pooled before a hot reload.
                selected_connection = pooled_entry
                selected_created_at = now
                break

    for expired in expired_connections:
        try:
            await _run_turso_call(
                expired.close,
                timeout=_TURSO_CLOSE_TIMEOUT_SECONDS,
            )
        except Exception:
            pass
    return selected_connection, selected_created_at


async def _validated_pooled_turso_wrapper():
    conn, created_at = await _take_pooled_turso_connection()
    if conn is None:
        return None
    _DB_CONNECTION_STATS["pooled"] += 1
    _record_connection_event("pooled")
    candidate = _PooledAsyncDB(conn, created_at=created_at)
    try:
        # Hrana streams expire server-side while a pooled connection is idle.
        await asyncio.wait_for(candidate.execute("SELECT 1"), timeout=3)
        return candidate
    except Exception as exc:
        candidate.has_error = True
        await candidate.close()
        _DB_CONNECTION_STATS["discarded"] += 1
        _record_connection_event("discarded")
        logger.info("Discarded stale Turso connection before reuse: %s", exc)
        return None


async def get_db(*, fresh: bool = False):
    """Open a database connection, optionally bypassing the Turso pool."""
    if TURSO_URL:
        import libsql
        wrapper = None if fresh else await _validated_pooled_turso_wrapper()

        if wrapper is None:
            async with get_turso_connect_semaphore():
                # Another request may have returned a healthy connection while
                # this one waited for a connect slot.
                if not fresh:
                    wrapper = await _validated_pooled_turso_wrapper()
                if wrapper is None:
                    connect_started_at = time.monotonic()
                    try:
                        conn = await asyncio.wait_for(
                            asyncio.to_thread(libsql.connect, TURSO_URL, auth_token=TURSO_TOKEN),
                            timeout=5,
                        )
                    except Exception as exc:
                        _record_db_operation("connect", connect_started_at, False)
                        _record_db_connection_error(exc, "connect")
                        raise
                    _record_db_operation("connect", connect_started_at, True)
                    _DB_CONNECTION_STATS["fresh"] += 1
                    _record_connection_event("fresh")
                    wrapper = _PooledAsyncDB(conn, return_to_pool=not fresh)
                    try:
                        await asyncio.wait_for(wrapper.execute("PRAGMA foreign_keys = ON"), timeout=3)
                    except Exception as exc:
                        wrapper.has_error = True
                        await wrapper.close()
                        logger.warning("Turso connection initialization failed: %s", exc)
                        raise
        return wrapper
    else:
        global _sqlite_wal_configured
        import aiosqlite
        db = await aiosqlite.connect(os.environ.get("DB_PATH", "bot_data.db"))
        db.row_factory = aiosqlite.Row
        if not _sqlite_wal_configured:
            await db.execute("PRAGMA journal_mode = WAL")
            _sqlite_wal_configured = True
        await db.execute("PRAGMA synchronous = NORMAL")
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("PRAGMA foreign_keys = ON")
        return db


# ══════════════════════════════════════════════
#  init_db() — Crée les tables
# ══════════════════════════════════════════════

async def init_db() -> None:
    """Crée toutes les tables nécessaires si elles n'existent pas encore."""
    db = await get_db()
    try:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
        )
        version_row = await cursor.fetchone()
        current_version = int(version_row["version"] if version_row else 0)
        run_legacy_bootstrap = current_version < 1

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
                description_vi TEXT DEFAULT '',
                description_ru TEXT DEFAULT '',
                price_usd REAL NOT NULL,
                warranty_days INTEGER DEFAULT 0,
                emoji TEXT DEFAULT '📦',
                custom_emoji_id TEXT DEFAULT NULL,
                image_url TEXT DEFAULT NULL,
                telegram_file_id TEXT DEFAULT NULL,
                delivery_type TEXT DEFAULT 'stock',
                dynamic_pricing_enabled INTEGER DEFAULT 0,
                dynamic_pricing_mode TEXT DEFAULT 'automatic',
                dynamic_min_price REAL DEFAULT NULL,
                dynamic_max_price REAL DEFAULT NULL,
                dynamic_base_price REAL DEFAULT NULL,
                dynamic_target_daily_sales REAL DEFAULT 1.0,
                dynamic_max_change_pct REAL DEFAULT 5.0,
                dynamic_cooldown_hours INTEGER DEFAULT 6,
                dynamic_sensitivity TEXT DEFAULT 'normal',
                dynamic_suggested_price REAL DEFAULT NULL,
                dynamic_last_calculated_at TIMESTAMP DEFAULT NULL,
                dynamic_daily_cap_pct REAL DEFAULT 10.0,
                dynamic_weekly_cap_pct REAL DEFAULT 25.0,
                dynamic_min_confidence REAL DEFAULT 0.30,
                dynamic_psychological_rounding INTEGER DEFAULT 0,
                dynamic_last_input_hash TEXT DEFAULT NULL,
                dynamic_last_applied_hash TEXT DEFAULT NULL,
                dynamic_last_confidence REAL DEFAULT NULL,
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
            """CREATE TABLE IF NOT EXISTS dynamic_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                old_price REAL NOT NULL,
                new_price REAL NOT NULL,
                suggested_price REAL NOT NULL,
                mode TEXT NOT NULL,
                reason TEXT DEFAULT '',
                sales_3d REAL DEFAULT 0,
                sales_14d REAL DEFAULT 0,
                stock_count INTEGER,
                stock_days REAL,
                views_7d INTEGER DEFAULT 0,
                conversion_7d REAL DEFAULT 0,
                revenue_7d REAL DEFAULT 0,
                score REAL DEFAULT 0,
                confidence REAL DEFAULT 0,
                applied INTEGER DEFAULT 0,
                decision_key TEXT DEFAULT NULL,
                explanation TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            """CREATE TABLE IF NOT EXISTS reseller_product_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                price_usd REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                enforce_cost_floor INTEGER NOT NULL DEFAULT 1,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_telegram_id, product_id),
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
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
            """CREATE TABLE IF NOT EXISTS nowpayments_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                request_key TEXT UNIQUE NOT NULL,
                payment_id TEXT UNIQUE,
                provider_status TEXT DEFAULT 'creating',
                price_amount REAL NOT NULL,
                price_currency TEXT DEFAULT 'usd',
                pay_amount REAL,
                pay_currency TEXT DEFAULT 'usdtbsc',
                pay_address TEXT,
                actually_paid REAL DEFAULT 0,
                network TEXT,
                valid_until TEXT,
                raw_payload TEXT DEFAULT '{}',
                processing_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                notification_claimed_at TIMESTAMP,
                notified_at TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )""",
            """CREATE TABLE IF NOT EXISTS nowpayments_wallet_topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id INTEGER NOT NULL,
                request_key TEXT UNIQUE NOT NULL,
                payment_id TEXT UNIQUE,
                provider_status TEXT DEFAULT 'creating',
                wallet_amount REAL NOT NULL,
                price_amount REAL NOT NULL,
                price_currency TEXT DEFAULT 'usd',
                pay_amount REAL,
                pay_currency TEXT DEFAULT 'usdtbsc',
                pay_address TEXT,
                actually_paid REAL DEFAULT 0,
                network TEXT,
                valid_until TEXT,
                raw_payload TEXT DEFAULT '{}',
                processing_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                notification_claimed_at TIMESTAMP,
                notified_at TIMESTAMP,
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
            )""",
            """CREATE TABLE IF NOT EXISTS supplier_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_code TEXT NOT NULL DEFAULT 'canboso',
                external_product_id TEXT NOT NULL,
                local_product_id INTEGER UNIQUE,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                description_en TEXT DEFAULT '',
                description_fr TEXT DEFAULT '',
                description_ar TEXT DEFAULT '',
                description_zh TEXT DEFAULT '',
                description_vi TEXT DEFAULT '',
                description_ru TEXT DEFAULT '',
                base_price REAL NOT NULL DEFAULT 0,
                source_price REAL NOT NULL DEFAULT 0,
                source_currency TEXT NOT NULL DEFAULT 'USD',
                remote_stock INTEGER NOT NULL DEFAULT 0,
                warranty_days INTEGER NOT NULL DEFAULT 0,
                image_url TEXT DEFAULT '',
                emoji TEXT DEFAULT '📦',
                custom_name TEXT DEFAULT '',
                custom_emoji TEXT DEFAULT '',
                custom_emoji_id TEXT DEFAULT '',
                custom_warranty_days INTEGER DEFAULT NULL,
                custom_image_url TEXT DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 0,
                margin_type TEXT NOT NULL DEFAULT 'inherit',
                margin_value REAL,
                raw_payload TEXT DEFAULT '{}',
                last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(supplier_code, external_product_id)
            )""",
            """CREATE TABLE IF NOT EXISTS supplier_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                supplier_code TEXT NOT NULL DEFAULT 'canboso',
                external_product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                cost_usd REAL,
                revenue_usd REAL,
                cost_estimated INTEGER NOT NULL DEFAULT 0,
                external_order_id TEXT,
                delivered_items TEXT DEFAULT '[]',
                raw_payload TEXT DEFAULT '{}',
                error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS product_stock_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_telegram_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id),
                UNIQUE(product_id, user_telegram_id, notified_at)
            )""",
            """CREATE TABLE IF NOT EXISTS product_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_telegram_id INTEGER NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
            )""",
            """CREATE TABLE IF NOT EXISTS product_buy_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_telegram_id INTEGER NOT NULL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
            )""",
            """CREATE TABLE IF NOT EXISTS payment_review_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_kind TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                action TEXT NOT NULL,
                note TEXT DEFAULT '',
                actor TEXT NOT NULL DEFAULT 'dashboard',
                result_action TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        ]

        if run_legacy_bootstrap:
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
            "CREATE INDEX IF NOT EXISTS idx_stock_product_added ON stock_items(product_id, added_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_telegram_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_binance_id ON orders(binance_order_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_product_status ON orders(product_id, status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_nowpayments_order ON nowpayments_payments(order_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_nowpayments_status ON nowpayments_payments(provider_status, updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_nowpayments_topups_user ON nowpayments_wallet_topups(user_telegram_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_nowpayments_topups_status ON nowpayments_wallet_topups(provider_status, updated_at)",
            "ALTER TABLE nowpayments_payments ADD COLUMN notification_claimed_at TIMESTAMP",
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
            "ALTER TABLE products ADD COLUMN telegram_file_id TEXT DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT NULL",
        "INSERT OR IGNORE INTO settings (key, value) SELECT 'finance_bot_balance_binance', value FROM settings WHERE key = 'finance_bot_balance'",
            "ALTER TABLE promo_codes ADD COLUMN max_uses_per_user INTEGER DEFAULT 0",
            "CREATE TABLE IF NOT EXISTS promo_code_usages (id INTEGER PRIMARY KEY AUTOINCREMENT, promo_code_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, usage_count INTEGER DEFAULT 0, last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(promo_code_id, user_telegram_id))",
            "ALTER TABLE promo_codes ADD COLUMN applicable_product_ids TEXT DEFAULT NULL",
            "ALTER TABLE promo_codes ADD COLUMN max_qty_per_order INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN description_fr TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_ar TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_zh TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_vi TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN description_ru TEXT DEFAULT ''",
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
            "ALTER TABLE products ADD COLUMN activation_message_vi TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN activation_message_ru TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_fr TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_ar TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_zh TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_vi TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN confirmation_message_ru TEXT DEFAULT ''",
            "ALTER TABLE products ADD COLUMN sort_order INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN dynamic_pricing_enabled INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN dynamic_pricing_mode TEXT DEFAULT 'automatic'",
            "ALTER TABLE products ADD COLUMN dynamic_min_price REAL DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_max_price REAL DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_base_price REAL DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_target_daily_sales REAL DEFAULT 1.0",
            "ALTER TABLE products ADD COLUMN dynamic_max_change_pct REAL DEFAULT 5.0",
            "ALTER TABLE products ADD COLUMN dynamic_cooldown_hours INTEGER DEFAULT 6",
            "ALTER TABLE products ADD COLUMN dynamic_sensitivity TEXT DEFAULT 'normal'",
            "ALTER TABLE products ADD COLUMN dynamic_suggested_price REAL DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_last_calculated_at TIMESTAMP DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_daily_cap_pct REAL DEFAULT 10.0",
            "ALTER TABLE products ADD COLUMN dynamic_weekly_cap_pct REAL DEFAULT 25.0",
            "ALTER TABLE products ADD COLUMN dynamic_min_confidence REAL DEFAULT 0.30",
            "ALTER TABLE products ADD COLUMN dynamic_psychological_rounding INTEGER DEFAULT 0",
            "ALTER TABLE products ADD COLUMN dynamic_last_input_hash TEXT DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_last_applied_hash TEXT DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN dynamic_last_confidence REAL DEFAULT NULL",
            "CREATE TABLE IF NOT EXISTS dynamic_price_history (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, old_price REAL NOT NULL, new_price REAL NOT NULL, suggested_price REAL NOT NULL, mode TEXT NOT NULL, reason TEXT DEFAULT '', sales_3d REAL DEFAULT 0, sales_14d REAL DEFAULT 0, stock_count INTEGER, stock_days REAL, views_7d INTEGER DEFAULT 0, conversion_7d REAL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE)",
            "ALTER TABLE dynamic_price_history ADD COLUMN revenue_7d REAL DEFAULT 0",
            "ALTER TABLE dynamic_price_history ADD COLUMN score REAL DEFAULT 0",
            "ALTER TABLE dynamic_price_history ADD COLUMN confidence REAL DEFAULT 0",
            "ALTER TABLE dynamic_price_history ADD COLUMN applied INTEGER DEFAULT 0",
            "ALTER TABLE dynamic_price_history ADD COLUMN decision_key TEXT DEFAULT NULL",
            "ALTER TABLE dynamic_price_history ADD COLUMN explanation TEXT DEFAULT ''",
            "UPDATE dynamic_price_history SET applied = 1 WHERE mode IN ('automatic', 'manual') AND ABS(new_price - old_price) >= 0.005",
            "CREATE INDEX IF NOT EXISTS idx_dynamic_price_history_product ON dynamic_price_history(product_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_dynamic_price_history_applied ON dynamic_price_history(product_id, applied, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_products_dynamic_pricing ON products(dynamic_pricing_enabled, dynamic_last_calculated_at)",
            "CREATE INDEX IF NOT EXISTS idx_orders_activation_status ON orders(activation_status, status)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_keys_user ON reseller_api_keys(user_telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_keys_prefix ON reseller_api_keys(key_prefix)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_product_prices_user ON reseller_product_prices(user_telegram_id, is_active, expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_product_prices_product ON reseller_product_prices(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_reseller_orders_user ON reseller_order_links(reseller_user_telegram_id, created_at)",
            "CREATE TABLE IF NOT EXISTS product_stock_alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notified_at TIMESTAMP, UNIQUE(product_id, user_telegram_id, notified_at))",
            "CREATE TABLE IF NOT EXISTS product_views (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_alerts_unique_pending ON product_stock_alerts(product_id, user_telegram_id) WHERE notified_at IS NULL",
            "CREATE INDEX IF NOT EXISTS idx_stock_alerts_product_pending ON product_stock_alerts(product_id, notified_at)",
            "CREATE INDEX IF NOT EXISTS idx_product_views_product_date ON product_views(product_id, viewed_at)",
            "CREATE INDEX IF NOT EXISTS idx_product_views_date_product ON product_views(viewed_at, product_id)",
            "CREATE INDEX IF NOT EXISTS idx_product_views_user_product_date ON product_views(product_id, user_telegram_id, viewed_at)",
            "CREATE TABLE IF NOT EXISTS product_buy_clicks (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE INDEX IF NOT EXISTS idx_product_buy_clicks_product_date ON product_buy_clicks(product_id, clicked_at)",
            "CREATE INDEX IF NOT EXISTS idx_product_buy_clicks_date_product ON product_buy_clicks(clicked_at, product_id)",
            "CREATE INDEX IF NOT EXISTS idx_product_buy_clicks_user_product_date ON product_buy_clicks(product_id, user_telegram_id, clicked_at)",
            "CREATE TABLE IF NOT EXISTS payment_review_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_kind TEXT NOT NULL, payment_id TEXT NOT NULL, action TEXT NOT NULL, note TEXT DEFAULT '', actor TEXT NOT NULL DEFAULT 'dashboard', result_action TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE INDEX IF NOT EXISTS idx_payment_review_actions_payment ON payment_review_actions(payment_kind, payment_id, created_at DESC)",
            "ALTER TABLE nowpayments_payments ADD COLUMN cancelled_at TIMESTAMP DEFAULT NULL",
            "ALTER TABLE nowpayments_wallet_topups ADD COLUMN cancelled_at TIMESTAMP DEFAULT NULL",
            "CREATE INDEX IF NOT EXISTS idx_orders_product_date_status ON orders(product_id, created_at, status)",
            "CREATE TABLE IF NOT EXISTS supplier_products (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_code TEXT NOT NULL DEFAULT 'canboso', external_product_id TEXT NOT NULL, local_product_id INTEGER UNIQUE, name TEXT NOT NULL, description TEXT DEFAULT '', description_en TEXT DEFAULT '', description_fr TEXT DEFAULT '', description_ar TEXT DEFAULT '', description_zh TEXT DEFAULT '', description_vi TEXT DEFAULT '', description_ru TEXT DEFAULT '', base_price REAL NOT NULL DEFAULT 0, source_price REAL NOT NULL DEFAULT 0, source_currency TEXT NOT NULL DEFAULT 'USD', remote_stock INTEGER NOT NULL DEFAULT 0, warranty_days INTEGER NOT NULL DEFAULT 0, image_url TEXT DEFAULT '', emoji TEXT DEFAULT '📦', custom_name TEXT DEFAULT '', custom_emoji TEXT DEFAULT '', custom_emoji_id TEXT DEFAULT '', custom_warranty_days INTEGER DEFAULT NULL, custom_image_url TEXT DEFAULT '', enabled INTEGER NOT NULL DEFAULT 0, margin_type TEXT NOT NULL DEFAULT 'inherit', margin_value REAL, raw_payload TEXT DEFAULT '{}', last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(supplier_code, external_product_id))",
            "CREATE TABLE IF NOT EXISTS supplier_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL UNIQUE, supplier_code TEXT NOT NULL DEFAULT 'canboso', external_product_id TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'pending', cost_usd REAL, revenue_usd REAL, cost_estimated INTEGER NOT NULL DEFAULT 0, external_order_id TEXT, delivered_items TEXT DEFAULT '[]', raw_payload TEXT DEFAULT '{}', error TEXT, attempts INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP)",
            "CREATE INDEX IF NOT EXISTS idx_supplier_products_local ON supplier_products(local_product_id)",
            "CREATE INDEX IF NOT EXISTS idx_supplier_products_enabled ON supplier_products(supplier_code, enabled)",
            "CREATE INDEX IF NOT EXISTS idx_supplier_orders_status ON supplier_orders(status, updated_at)",
        ]
        table_columns: dict[str, set[str]] = {}
        migration_errors: list[tuple[str, Exception]] = []

        async def _columns_for(table_name: str) -> set[str]:
            if table_name not in table_columns:
                cursor = await db.execute(f"PRAGMA table_info({table_name})")
                table_columns[table_name] = {
                    str(row["name"]) for row in await cursor.fetchall()
                }
            return table_columns[table_name]

        if run_legacy_bootstrap:
            for sql in migrations:
                try:
                    parts = sql.strip().split()
                    if len(parts) >= 6 and parts[:2] == ["ALTER", "TABLE"] and parts[3:5] == ["ADD", "COLUMN"]:
                        table_name = parts[2]
                        column_name = parts[5]
                        columns = await _columns_for(table_name)
                        if column_name in columns:
                            continue
                        await db.execute(sql)
                        columns.add(column_name)
                        continue
                    await db.execute(sql)
                except Exception as e:
                    migration_errors.append((sql, e))
                    logger.warning("Migration failed for %s: %s", sql, e)
            await db.commit()
            if not migration_errors:
                await db.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (1, ?)",
                    ("legacy_schema_bootstrap",),
                )
                await db.commit()
                current_version = 1
            else:
                logger.warning(
                    "Legacy schema bootstrap remains pending after %d migration error(s)",
                    len(migration_errors),
                )

        if 1 <= current_version < 2:
            version_two_statements = [
                """CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    progress_done INTEGER NOT NULL DEFAULT 0,
                    progress_failed INTEGER NOT NULL DEFAULT 0,
                    progress_total INTEGER NOT NULL DEFAULT 0,
                    cursor_value INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    available_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    claimed_at TIMESTAMP,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )""",
                "CREATE INDEX IF NOT EXISTS idx_background_jobs_ready ON background_jobs(status, available_at, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_background_jobs_claimed ON background_jobs(status, claimed_at)",
                """CREATE TABLE IF NOT EXISTS performance_action_hourly (
                    bucket_hour TEXT NOT NULL,
                    action TEXT NOT NULL,
                    sample_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    total_duration_ms REAL NOT NULL DEFAULT 0,
                    max_duration_ms REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (bucket_hour, action)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_performance_action_hour ON performance_action_hourly(bucket_hour)",
            ]
            for sql in version_two_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (2, ?)",
                ("persistent_jobs_and_performance_history",),
            )
            await db.commit()
            current_version = 2

        if 2 <= current_version < 3:
            version_three_statements = [
                """CREATE TABLE IF NOT EXISTS game_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL DEFAULT 'football-data',
                    external_match_id TEXT NOT NULL,
                    competition_code TEXT DEFAULT '',
                    competition_name TEXT NOT NULL DEFAULT '',
                    competition_emblem TEXT DEFAULT '',
                    stage TEXT DEFAULT '',
                    home_external_id TEXT DEFAULT '',
                    home_name TEXT NOT NULL,
                    home_code TEXT DEFAULT '',
                    home_crest TEXT DEFAULT '',
                    away_external_id TEXT DEFAULT '',
                    away_name TEXT NOT NULL,
                    away_code TEXT DEFAULT '',
                    away_crest TEXT DEFAULT '',
                    utc_date TEXT NOT NULL,
                    provider_status TEXT NOT NULL DEFAULT 'SCHEDULED',
                    provider_winner TEXT,
                    score_home INTEGER,
                    score_away INTEGER,
                    regular_score_home INTEGER,
                    regular_score_away INTEGER,
                    market_type TEXT NOT NULL DEFAULT 'qualified',
                    status TEXT NOT NULL DEFAULT 'DRAFT',
                    lock_at TEXT NOT NULL,
                    min_stake INTEGER NOT NULL DEFAULT 25,
                    max_stake INTEGER NOT NULL DEFAULT 500,
                    fee_bps INTEGER NOT NULL DEFAULT 500,
                    result_outcome TEXT,
                    raw_payload TEXT NOT NULL DEFAULT '{}',
                    last_synced_at TEXT,
                    next_sync_at TEXT,
                    published_at TEXT,
                    settled_at TEXT,
                    cancelled_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider, external_match_id)
                )""",
                """CREATE TABLE IF NOT EXISTS game_wallets (
                    user_telegram_id INTEGER PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0,
                    last_claim_date TEXT,
                    lifetime_earned INTEGER NOT NULL DEFAULT 0,
                    lifetime_spent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
                )""",
                """CREATE TABLE IF NOT EXISTS game_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    user_telegram_id INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    stake INTEGER NOT NULL,
                    payout INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    settled_at TEXT,
                    UNIQUE(match_id, user_telegram_id),
                    FOREIGN KEY (match_id) REFERENCES game_matches(id),
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
                )""",
                """CREATE TABLE IF NOT EXISTS game_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_telegram_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    reference_type TEXT DEFAULT '',
                    reference_id TEXT DEFAULT '',
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_game_matches_status_lock ON game_matches(status, lock_at)",
                "CREATE INDEX IF NOT EXISTS idx_game_matches_sync ON game_matches(status, next_sync_at)",
                "CREATE INDEX IF NOT EXISTS idx_game_matches_date ON game_matches(utc_date)",
                "CREATE INDEX IF NOT EXISTS idx_game_bets_match_outcome ON game_bets(match_id, outcome, status)",
                "CREATE INDEX IF NOT EXISTS idx_game_bets_user_created ON game_bets(user_telegram_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_game_ledger_user_created ON game_ledger(user_telegram_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_game_wallets_balance ON game_wallets(balance DESC)",
            ]
            for sql in version_three_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (3, ?)",
                ("virtual_match_game",),
            )
            await db.commit()
            current_version = 3

        if 3 <= current_version < 4:
            supplier_description_columns = {
                "description_en": "TEXT DEFAULT ''",
                "description_fr": "TEXT DEFAULT ''",
                "description_ar": "TEXT DEFAULT ''",
                "description_zh": "TEXT DEFAULT ''",
                "description_vi": "TEXT DEFAULT ''",
                "description_ru": "TEXT DEFAULT ''",
            }
            columns = await _columns_for("supplier_products")
            for column_name, column_type in supplier_description_columns.items():
                if column_name not in columns:
                    await db.execute(
                        f"ALTER TABLE supplier_products ADD COLUMN {column_name} {column_type}"
                    )
                    columns.add(column_name)

            # Preserve descriptions previously edited through the regular product editor.
            await db.execute(
                """UPDATE supplier_products
                   SET description_en = CASE
                           WHEN TRIM(COALESCE(description_en, '')) <> '' THEN description_en
                           WHEN TRIM(COALESCE((SELECT p.description FROM products p WHERE p.id = supplier_products.local_product_id), ''))
                                <> TRIM(COALESCE(description, ''))
                           THEN COALESCE((SELECT p.description FROM products p WHERE p.id = supplier_products.local_product_id), '')
                           ELSE ''
                       END,
                       description_fr = CASE WHEN TRIM(COALESCE(description_fr, '')) <> '' THEN description_fr ELSE COALESCE((SELECT p.description_fr FROM products p WHERE p.id = supplier_products.local_product_id), '') END,
                       description_ar = CASE WHEN TRIM(COALESCE(description_ar, '')) <> '' THEN description_ar ELSE COALESCE((SELECT p.description_ar FROM products p WHERE p.id = supplier_products.local_product_id), '') END,
                       description_zh = CASE WHEN TRIM(COALESCE(description_zh, '')) <> '' THEN description_zh ELSE COALESCE((SELECT p.description_zh FROM products p WHERE p.id = supplier_products.local_product_id), '') END,
                       description_vi = CASE WHEN TRIM(COALESCE(description_vi, '')) <> '' THEN description_vi ELSE COALESCE((SELECT p.description_vi FROM products p WHERE p.id = supplier_products.local_product_id), '') END,
                       description_ru = CASE WHEN TRIM(COALESCE(description_ru, '')) <> '' THEN description_ru ELSE COALESCE((SELECT p.description_ru FROM products p WHERE p.id = supplier_products.local_product_id), '') END
                   WHERE local_product_id IS NOT NULL"""
            )
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (4, ?)",
                ("supplier_multilingual_descriptions",),
            )
            await db.commit()
            current_version = 4

        if 4 <= current_version < 5:
            columns = await _columns_for("supplier_products")
            if "source_price" not in columns:
                await db.execute(
                    "ALTER TABLE supplier_products ADD COLUMN source_price REAL NOT NULL DEFAULT 0"
                )
                columns.add("source_price")
            if "source_currency" not in columns:
                await db.execute(
                    "ALTER TABLE supplier_products ADD COLUMN source_currency TEXT NOT NULL DEFAULT 'USD'"
                )
                columns.add("source_currency")
            if "base_price" in columns:
                await db.execute(
                    """UPDATE supplier_products
                       SET source_price = base_price,
                           source_currency = 'USD'
                       WHERE source_price = 0 AND base_price <> 0"""
                )
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (5, ?)",
                ("multi_supplier_source_currency",),
            )
            await db.commit()
            current_version = 5

        if 5 <= current_version < 6:
            supplier_customization_columns = {
                "custom_name": "TEXT DEFAULT ''",
                "custom_emoji": "TEXT DEFAULT ''",
                "custom_emoji_id": "TEXT DEFAULT ''",
            }
            columns = await _columns_for("supplier_products")
            for column_name, column_type in supplier_customization_columns.items():
                if column_name not in columns:
                    await db.execute(
                        f"ALTER TABLE supplier_products ADD COLUMN {column_name} {column_type}"
                    )
                    columns.add(column_name)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (6, ?)",
                ("supplier_product_customization",),
            )
            await db.commit()
            current_version = 6

        if 6 <= current_version < 7:
            columns = await _columns_for("supplier_products")
            if "custom_warranty_days" not in columns:
                await db.execute(
                    "ALTER TABLE supplier_products ADD COLUMN custom_warranty_days INTEGER DEFAULT NULL"
                )
                columns.add("custom_warranty_days")
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (7, ?)",
                ("supplier_custom_warranty",),
            )
            await db.commit()
            current_version = 7

        if 7 <= current_version < 8:
            columns = await _columns_for("supplier_products")
            if "custom_image_url" not in columns:
                await db.execute(
                    "ALTER TABLE supplier_products ADD COLUMN custom_image_url TEXT DEFAULT ''"
                )
                columns.add("custom_image_url")

            # Preserve image links already edited through the regular product editor.
            product_columns = await _columns_for("products")
            if "image_url" in product_columns:
                await db.execute(
                    """UPDATE supplier_products
                       SET custom_image_url = COALESCE(
                           (SELECT p.image_url FROM products p
                            WHERE p.id = supplier_products.local_product_id),
                           ''
                       )
                       WHERE local_product_id IS NOT NULL
                         AND TRIM(COALESCE(custom_image_url, '')) = ''
                         AND TRIM(COALESCE(
                             (SELECT p.image_url FROM products p
                              WHERE p.id = supplier_products.local_product_id),
                             ''
                         )) <> ''
                         AND TRIM(COALESCE(
                             (SELECT p.image_url FROM products p
                              WHERE p.id = supplier_products.local_product_id),
                             ''
                         )) <> TRIM(COALESCE(image_url, ''))"""
                )
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (8, ?)",
                ("supplier_custom_image",),
            )
            await db.commit()
            current_version = 8

        if 8 <= current_version < 9:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS supplier_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL UNIQUE,
                    supplier_code TEXT NOT NULL DEFAULT 'canboso',
                    external_product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending',
                    cost_usd REAL,
                    revenue_usd REAL,
                    cost_estimated INTEGER NOT NULL DEFAULT 0,
                    external_order_id TEXT,
                    delivered_items TEXT DEFAULT '[]',
                    raw_payload TEXT DEFAULT '{}',
                    error TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )"""
            )
            columns = await _columns_for("supplier_orders")
            financial_columns = {
                "cost_usd": "REAL",
                "revenue_usd": "REAL",
                "cost_estimated": "INTEGER NOT NULL DEFAULT 0",
            }
            for column_name, column_type in financial_columns.items():
                if column_name not in columns:
                    await db.execute(
                        f"ALTER TABLE supplier_orders ADD COLUMN {column_name} {column_type}"
                    )
                    columns.add(column_name)

            # Historical revenue is exact. Historical supplier cost is an
            # estimate based on the latest known catalog cost.
            order_columns = await _columns_for("orders")
            if "amount_usd" in order_columns:
                await db.execute(
                    """UPDATE supplier_orders
                       SET revenue_usd = (
                           SELECT o.amount_usd FROM orders o
                           WHERE o.id = supplier_orders.order_id
                       )
                       WHERE revenue_usd IS NULL"""
                )
            supplier_product_columns = await _columns_for("supplier_products")
            if {
                "supplier_code",
                "external_product_id",
                "base_price",
            } <= supplier_product_columns:
                await db.execute(
                    """UPDATE supplier_orders
                       SET cost_usd = (
                               SELECT sp.base_price * supplier_orders.quantity
                               FROM supplier_products sp
                               WHERE sp.supplier_code = supplier_orders.supplier_code
                                 AND sp.external_product_id = supplier_orders.external_product_id
                               LIMIT 1
                           ),
                           cost_estimated = CASE
                               WHEN EXISTS (
                                   SELECT 1 FROM supplier_products sp
                                   WHERE sp.supplier_code = supplier_orders.supplier_code
                                     AND sp.external_product_id = supplier_orders.external_product_id
                               ) THEN 1 ELSE cost_estimated END
                       WHERE cost_usd IS NULL"""
                )
            if {"supplier_code", "status", "completed_at"} <= columns:
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_supplier_orders_supplier_completed "
                    "ON supplier_orders(supplier_code, status, completed_at)"
                )
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (9, ?)",
                ("supplier_order_financial_snapshots",),
            )
            await db.commit()
            current_version = 9

        if 9 <= current_version < 10:
            version_ten_statements = [
                """CREATE TABLE IF NOT EXISTS webhook_autoscale_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    mode TEXT NOT NULL DEFAULT 'auto',
                    observe_only INTEGER NOT NULL DEFAULT 1,
                    min_workers INTEGER NOT NULL DEFAULT 6,
                    max_workers INTEGER NOT NULL DEFAULT 20,
                    manual_workers INTEGER NOT NULL DEFAULT 8,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE IF NOT EXISTS webhook_autoscale_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    bottleneck TEXT NOT NULL,
                    workers_before INTEGER NOT NULL,
                    workers_after INTEGER NOT NULL,
                    proposed_workers INTEGER NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    observe_only INTEGER NOT NULL DEFAULT 1,
                    next_analysis_seconds INTEGER NOT NULL DEFAULT 60,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                "CREATE INDEX IF NOT EXISTS idx_webhook_autoscale_decisions_created ON webhook_autoscale_decisions(created_at DESC)",
                """INSERT OR IGNORE INTO webhook_autoscale_settings
                   (id, mode, observe_only, min_workers, max_workers, manual_workers)
                   VALUES (1, 'auto', 1, 6, 20, 8)""",
            ]
            for sql in version_ten_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (10, ?)",
                ("webhook_worker_autoscaling",),
            )
            await db.commit()
            current_version = 10

        if 10 <= current_version < 11:
            reseller_key_columns = await _columns_for("reseller_api_keys")
            reseller_security_columns = {
                "ip_allowlist": "TEXT NOT NULL DEFAULT '[]'",
                "webhook_url": "TEXT NOT NULL DEFAULT ''",
                "webhook_enabled": "INTEGER NOT NULL DEFAULT 0",
                "webhook_secret_salt": "TEXT NOT NULL DEFAULT ''",
            }
            if reseller_key_columns:
                for column_name, column_type in reseller_security_columns.items():
                    if column_name not in reseller_key_columns:
                        await db.execute(
                            f"ALTER TABLE reseller_api_keys ADD COLUMN {column_name} {column_type}"
                        )
                        reseller_key_columns.add(column_name)

            reseller_order_columns = await _columns_for("reseller_order_links")
            if reseller_order_columns and "request_fingerprint" not in reseller_order_columns:
                await db.execute(
                    "ALTER TABLE reseller_order_links ADD COLUMN request_fingerprint TEXT DEFAULT NULL"
                )
                reseller_order_columns.add("request_fingerprint")

            version_eleven_statements = [
                """CREATE TABLE IF NOT EXISTS reseller_deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id TEXT NOT NULL UNIQUE,
                    reseller_api_key_id INTEGER NOT NULL,
                    user_telegram_id INTEGER NOT NULL,
                    topup_id INTEGER NOT NULL UNIQUE,
                    idempotency_key TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL,
                    reference TEXT NOT NULL DEFAULT '',
                    network TEXT NOT NULL DEFAULT 'BEP20',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_telegram_id, idempotency_key),
                    FOREIGN KEY (reseller_api_key_id) REFERENCES reseller_api_keys(id),
                    FOREIGN KEY (topup_id) REFERENCES nowpayments_wallet_topups(id),
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_reseller_deposits_user_created ON reseller_deposits(user_telegram_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_reseller_deposits_topup ON reseller_deposits(topup_id)",
                """CREATE TABLE IF NOT EXISTS reseller_test_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reseller_api_key_id INTEGER NOT NULL,
                    user_telegram_id INTEGER NOT NULL,
                    idempotency_key TEXT,
                    request_fingerprint TEXT,
                    customer_reference TEXT NOT NULL DEFAULT '',
                    quantity INTEGER NOT NULL DEFAULT 1,
                    amount_usd REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    item_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_telegram_id, idempotency_key),
                    FOREIGN KEY (reseller_api_key_id) REFERENCES reseller_api_keys(id),
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_reseller_test_orders_user_created ON reseller_test_orders(user_telegram_id, created_at DESC)",
            ]
            for sql in version_eleven_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (11, ?)",
                ("reseller_wallet_deposits_and_security",),
            )
            await db.commit()
            current_version = 11

        if 11 <= current_version < 12:
            version_twelve_statements = [
                """CREATE TABLE IF NOT EXISTS supplier_product_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_product_id INTEGER NOT NULL,
                    supplier_product_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'proposed',
                    confidence REAL NOT NULL DEFAULT 0,
                    match_source TEXT NOT NULL DEFAULT 'deterministic',
                    reason TEXT NOT NULL DEFAULT '',
                    attributes_json TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    UNIQUE(local_product_id, supplier_product_id),
                    FOREIGN KEY (local_product_id) REFERENCES products(id),
                    FOREIGN KEY (supplier_product_id) REFERENCES supplier_products(id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_supplier_routes_local_status ON supplier_product_routes(local_product_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_routes_mapping_status ON supplier_product_routes(supplier_product_id, status)",
            ]
            for sql in version_twelve_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (12, ?)",
                ("multi_supplier_product_router",),
            )
            await db.commit()
            current_version = 12

        if 12 <= current_version < 13:
            version_thirteen_statements = [
                """CREATE TABLE IF NOT EXISTS supplier_product_analysis (
                    supplier_product_id INTEGER PRIMARY KEY,
                    supplier_code TEXT NOT NULL,
                    family TEXT NOT NULL DEFAULT '',
                    duration_months INTEGER,
                    duration_days INTEGER,
                    delivery_mode TEXT NOT NULL DEFAULT 'unknown',
                    access_mode TEXT NOT NULL DEFAULT 'unknown',
                    region TEXT NOT NULL DEFAULT '',
                    tokens_json TEXT NOT NULL DEFAULT '[]',
                    analysis_source TEXT NOT NULL DEFAULT 'deterministic',
                    confidence REAL NOT NULL DEFAULT 0,
                    source_hash TEXT NOT NULL,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (supplier_product_id) REFERENCES supplier_products(id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_supplier_analysis_family_duration ON supplier_product_analysis(family, duration_months, duration_days)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_analysis_code ON supplier_product_analysis(supplier_code)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_orders_product_status ON supplier_orders(supplier_code, external_product_id, status)",
            ]
            for sql in version_thirteen_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (13, ?)",
                ("supplier_ai_search_index",),
            )
            await db.commit()
            current_version = 13

        if 13 <= current_version < 14:
            version_fourteen_statements = [
                """CREATE TABLE IF NOT EXISTS reseller_product_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_telegram_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    price_usd REAL NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    enforce_cost_floor INTEGER NOT NULL DEFAULT 1,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_telegram_id, product_id),
                    FOREIGN KEY (user_telegram_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_reseller_product_prices_user ON reseller_product_prices(user_telegram_id, is_active, expires_at)",
                "CREATE INDEX IF NOT EXISTS idx_reseller_product_prices_product ON reseller_product_prices(product_id)",
            ]
            for sql in version_fourteen_statements:
                await db.execute(sql)
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (14, ?)",
                ("reseller_special_product_prices",),
            )
            await db.commit()
            current_version = 14

        if 14 <= current_version < 15:
            reseller_price_columns = await _columns_for("reseller_product_prices")
            if "apply_to_telegram" not in reseller_price_columns:
                await db.execute(
                    "ALTER TABLE reseller_product_prices "
                    "ADD COLUMN apply_to_telegram INTEGER NOT NULL DEFAULT 1"
                )
                reseller_price_columns.add("apply_to_telegram")
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (15, ?)",
                ("reseller_special_price_scope",),
            )
            await db.commit()
            current_version = 15

        if 15 <= current_version < 16:
            await db.execute(
                """CREATE INDEX IF NOT EXISTS idx_reseller_prices_telegram_active
                   ON reseller_product_prices(user_telegram_id, product_id, expires_at)
                   WHERE is_active = 1 AND apply_to_telegram = 1"""
            )
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (16, ?)",
                ("reseller_telegram_price_cache_index",),
            )
            await db.commit()
            current_version = 16

    finally:
        await db.close()
