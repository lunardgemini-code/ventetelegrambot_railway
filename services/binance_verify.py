# services/binance_verify.py — Vérification des paiements Binance Pay
# Utilise l'API SAPI de Binance pour consulter l'historique des transactions.

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time

import httpx

from config import BINANCE_API_KEY, BINANCE_API_SECRET
from services.runtime_metrics import dependency_call

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────
BASE_URL = "https://api.binance.com/sapi/v1/pay/transactions"
RECV_WINDOW = 5000
# Tolérance de comparaison des montants (en USD)
AMOUNT_TOLERANCE = 0.01
# Fenetre de recherche des depots internes (en millisecondes) : 2 heures
SEARCH_WINDOW_MS = 2 * 60 * 60 * 1000
# Binance Pay payments can be submitted after the order timeout. Search the
# current two-hour window first, then bounded older windows up to 48 hours.
PAY_SEARCH_WINDOW_MS = 48 * 60 * 60 * 1000
PAY_INITIAL_WINDOW_MS = 2 * 60 * 60 * 1000
PAY_FALLBACK_WINDOW_MS = 4 * 60 * 60 * 1000
PAY_MIN_SPLIT_WINDOW_MS = 5 * 60 * 1000
PAY_API_LIMIT = 100
PAY_MAX_API_REQUESTS = 24
_HTTP_CLIENT: httpx.AsyncClient | None = None
_VERIFY_MISS_TTL_SECONDS = 5.0
_VERIFY_HIT_TTL_SECONDS = 300.0
_VERIFY_CACHE_MAX = 512
_VERIFY_CACHE: dict[str, tuple[float, dict]] = {}
_VERIFY_TASKS: dict[str, tuple[object, asyncio.Task]] = {}


def _verification_key(
    client_order_id: str,
    expected_amount: float,
    api_key: str,
) -> str:
    account = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
    return f"{account}:{str(client_order_id).strip().upper()}:{float(expected_amount):.8f}"


def _prune_verification_cache(now: float) -> None:
    expired = [key for key, (expires_at, _) in _VERIFY_CACHE.items() if expires_at <= now]
    for key in expired:
        _VERIFY_CACHE.pop(key, None)
    if len(_VERIFY_CACHE) > _VERIFY_CACHE_MAX:
        for key, _ in sorted(_VERIFY_CACHE.items(), key=lambda item: item[1][0])[
            : len(_VERIFY_CACHE) - _VERIFY_CACHE_MAX
        ]:
            _VERIFY_CACHE.pop(key, None)


def reset_binance_verification_cache() -> None:
    _VERIFY_CACHE.clear()
    _VERIFY_TASKS.clear()


async def _get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=10.0)
    return _HTTP_CLIENT


def _generate_signature(query_string: str, secret: str) -> str:
    """Génère la signature HMAC-SHA256 pour l'API Binance."""
    return hmac.new(
        secret.encode(),
        query_string.encode(),
        hashlib.sha256,
    ).hexdigest()


def _payment_search_ranges(now_ms: int) -> list[tuple[int, int]]:
    """Build newest-first, non-overlapping ranges for Binance Pay history."""
    oldest_ms = now_ms - PAY_SEARCH_WINDOW_MS
    ranges: list[tuple[int, int]] = []
    end_ms = now_ms
    window_ms = PAY_INITIAL_WINDOW_MS
    while end_ms > oldest_ms:
        start_ms = max(oldest_ms, end_ms - window_ms)
        ranges.append((start_ms, end_ms))
        end_ms = start_ms
        window_ms = PAY_FALLBACK_WINDOW_MS
    return ranges


def _payment_matches(
    transaction: dict,
    client_order_id: str,
    expected_amount: float,
) -> bool:
    try:
        tx_amount = float(transaction.get("amount", 0))
    except (TypeError, ValueError):
        return False

    tx_id = str(transaction.get("transactionId", "")).strip().upper()
    tx_order_id = str(transaction.get("orderId", "")).strip().upper()
    tx_order_type = str(transaction.get("orderType", "")).strip().upper()
    cleaned_client_id = client_order_id.strip().upper()

    is_incoming = tx_order_type in (
        "C2C",
        "PAY",
        "CRYPTO_BOX",
        "TRANSFER",
        "1",
    )
    id_match = cleaned_client_id in (tx_id, tx_order_id)

    # Overpayments are valid. Only reject an amount that is below what the
    # order requires (allowing the existing one-cent rounding tolerance).
    amount_sufficient = tx_amount + AMOUNT_TOLERANCE >= expected_amount
    return id_match and is_incoming and amount_sufficient


async def _fetch_pay_transactions(
    start_ms: int,
    end_ms: int,
    api_key: str,
    api_secret: str,
) -> tuple[list[dict] | None, str | None]:
    request_ms = int(time.time() * 1000)
    query_string = (
        f"timestamp={request_ms}"
        f"&recvWindow={RECV_WINDOW}"
        f"&startTime={start_ms}"
        f"&endTime={end_ms}"
        f"&limit={PAY_API_LIMIT}"
    )
    signature = _generate_signature(query_string, api_secret)
    full_url = f"{BASE_URL}?{query_string}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": api_key,
        "Content-Type": "application/json",
    }

    client = await _get_http_client()
    async with dependency_call("binance", circuit_breaker=False):
        response = await client.get(full_url, headers=headers, timeout=5.0)
    if response.status_code != 200:
        return None, (
            f"Erreur API Binance - HTTP {response.status_code} : "
            f"{response.text[:200]}"
        )

    data = response.json()
    if data.get("code") != "000000":
        return None, (
            f"Erreur API Binance - code {data.get('code')} : "
            f"{data.get('message', 'Erreur inconnue')}"
        )
    return list(data.get("data") or []), None


async def _verify_payment_uncached(
    client_order_id: str,
    expected_amount: float,
    api_key: str | None = None,
    api_secret: str | None = None,
    lang: str = "fr",
) -> dict:
    """Vérifie un paiement Binance Pay en consultant l'historique des transactions."""
    result: dict = {"verified": False, "transaction": None, "error": None}

    key_to_use = api_key if api_key else BINANCE_API_KEY
    secret_to_use = api_secret if api_secret else BINANCE_API_SECRET

    if not key_to_use or not secret_to_use:
        result["error"] = {"en": "Binance API keys not configured.", "ar": "مفاتيح Binance API غير مهيأة."}.get(lang, "Clés API Binance non configurées.")
        logger.error(result["error"])
        return result

    try:
        now_ms = int(time.time() * 1000)
        ranges = _payment_search_ranges(now_ms)
        pending_ranges = list(ranges)
        request_count = 0
        transaction_count = 0

        while pending_ranges and request_count < PAY_MAX_API_REQUESTS:
            start_ms, end_ms = pending_ranges.pop(0)
            transactions, error = await _fetch_pay_transactions(
                start_ms,
                end_ms,
                key_to_use,
                secret_to_use,
            )
            request_count += 1
            if error:
                result["error"] = error
                logger.error(result["error"])
                return result

            transactions = transactions or []
            transaction_count += len(transactions)
            for tx in transactions:
                if _payment_matches(tx, client_order_id, expected_amount):
                    result["verified"] = True
                    result["transaction"] = tx
                    logger.info(
                        "Paiement verifie - Transaction ID: %s, montant: %s, requests: %d",
                        tx.get("transactionId", ""),
                        tx.get("amount", 0),
                        request_count,
                    )
                    return result

            # A full response may be truncated. Split that range and search the
            # newest half first so recent customer payments remain fast.
            if (
                len(transactions) >= PAY_API_LIMIT
                and end_ms - start_ms > PAY_MIN_SPLIT_WINDOW_MS
                and request_count + len(pending_ranges) < PAY_MAX_API_REQUESTS
            ):
                midpoint = start_ms + (end_ms - start_ms) // 2
                pending_ranges[0:0] = [
                    (midpoint, end_ms),
                    (start_ms, midpoint),
                ]

        # Aucune correspondance trouvée
        result["error"] = {"en": f"No transaction found matching ID={client_order_id}, amount={expected_amount}", "ar": f"لم يتم العثور على معاملة مطابقة للمعرف={client_order_id} والمبلغ={expected_amount}"}.get(lang, f"Aucune transaction correspondante trouvée. Recherché : ID={client_order_id}, montant={expected_amount}")
        logger.info(
            "No matching Binance Pay transaction after %d request(s), %d row(s) scanned",
            request_count,
            transaction_count,
        )
        result["_cacheable_miss"] = True
        return result


    except (httpx.TimeoutException, TimeoutError):
        result["error"] = {"en": "Timeout connecting to Binance API.", "ar": "انتهت مهلة الاتصال بـ Binance API."}.get(lang, "Délai d'attente dépassé lors de la connexion à l'API Binance.")
        logger.exception(result["error"])
        return result
    except httpx.RequestError as exc:
        result["error"] = f"Erreur de connexion à l'API Binance : {exc}"
        logger.exception(result["error"])
        return result
    except Exception as exc:
        result["error"] = f"Erreur inattendue lors de la vérification : {exc}"
        logger.exception(result["error"])
        return result

async def verify_payment(
    client_order_id: str,
    expected_amount: float,
    api_key: str | None = None,
    api_secret: str | None = None,
    lang: str = "fr",
) -> dict:
    """Share identical checks and briefly cache definitive Binance misses."""
    key_to_use = api_key if api_key else BINANCE_API_KEY
    secret_to_use = api_secret if api_secret else BINANCE_API_SECRET
    if not key_to_use or not secret_to_use:
        return await _verify_payment_uncached(
            client_order_id,
            expected_amount,
            api_key=api_key,
            api_secret=api_secret,
            lang=lang,
        )

    cache_key = _verification_key(client_order_id, expected_amount, key_to_use)
    now = time.monotonic()
    _prune_verification_cache(now)
    cached = _VERIFY_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return dict(cached[1])

    loop = asyncio.get_running_loop()
    current = _VERIFY_TASKS.get(cache_key)
    if current is None or current[0] is not loop or current[1].done():
        task = asyncio.create_task(
            _verify_payment_uncached(
                client_order_id,
                expected_amount,
                api_key=api_key,
                api_secret=api_secret,
                lang=lang,
            )
        )
        _VERIFY_TASKS[cache_key] = (loop, task)
    else:
        task = current[1]

    try:
        raw_result = await asyncio.shield(task)
    finally:
        registered = _VERIFY_TASKS.get(cache_key)
        if registered and registered[1] is task and task.done():
            _VERIFY_TASKS.pop(cache_key, None)

    result = dict(raw_result)
    cacheable_miss = bool(result.pop("_cacheable_miss", False))
    if result.get("verified"):
        ttl = _VERIFY_HIT_TTL_SECONDS
    elif cacheable_miss:
        ttl = _VERIFY_MISS_TTL_SECONDS
    else:
        ttl = 0
    if ttl:
        _VERIFY_CACHE[cache_key] = (time.monotonic() + ttl, dict(result))
    return result


async def verify_internal_transfer(
    client_tx_id: str,
    expected_amount: float,
    api_key: str | None = None,
    api_secret: str | None = None,
    lang: str = "fr",
) -> dict:
    """Vérifie un transfert interne Binance (off-chain) via l'historique des dépôts."""
    result: dict = {"verified": False, "transaction": None, "error": None}

    key_to_use = api_key if api_key else BINANCE_API_KEY
    secret_to_use = api_secret if api_secret else BINANCE_API_SECRET

    if not key_to_use or not secret_to_use:
        result["error"] = {"en": "Binance API keys not configured.", "ar": "مفاتيح Binance API غير مهيأة."}.get(lang, "Clés API Binance non configurées.")
        logger.error(result["error"])
        return result

    now_ms = int(time.time() * 1000)
    start_ts = now_ms - SEARCH_WINDOW_MS
    
    DEPOSIT_URL = "https://api.binance.com/sapi/v1/capital/deposit/hisrec"

    query_string = (
        f"timestamp={now_ms}"
        f"&recvWindow={RECV_WINDOW}"
        f"&startTime={start_ts}"
        f"&endTime={now_ms}"
        f"&coin=USDT"
    )
    signature = _generate_signature(query_string, secret_to_use)
    full_url = f"{DEPOSIT_URL}?{query_string}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": key_to_use,
        "Content-Type": "application/json",
    }

    try:
        client = await _get_http_client()
        async with dependency_call("binance", circuit_breaker=False):
            response = await client.get(full_url, headers=headers, timeout=10.0)

        if response.status_code != 200:
            result["error"] = f"Erreur API Binance — HTTP {response.status_code} : {response.text[:200]}"
            logger.error(result["error"])
            return result

        deposits = response.json()
        if not isinstance(deposits, list):
            result["error"] = f"Erreur inattendue format API: {str(deposits)[:100]}"
            return result

        if not deposits:
            result["error"] = {"en": "No deposits found in the period.", "ar": "لم يتم العثور على إيداعات في هذه الفترة."}.get(lang, "Aucun dépôt trouvé dans la période.")
            return result

        cleaned_client_id = client_tx_id.strip().upper()

        for dep in deposits:
            tx_id = str(dep.get("txId", "")).strip().upper()
            tx_amount = float(dep.get("amount", 0))
            status = dep.get("status")

            # 1: Success status for deposit
            is_id_match = (
                cleaned_client_id == tx_id or
                f"OFF-CHAIN TRANSFER {cleaned_client_id}" == tx_id or
                cleaned_client_id.replace("OFF-CHAIN TRANSFER ", "") == tx_id.replace("OFF-CHAIN TRANSFER ", "")
            )
            amount_match = abs(tx_amount - expected_amount) <= AMOUNT_TOLERANCE

            if is_id_match and status == 1 and amount_match:
                result["verified"] = True
                result["transaction"] = dep
                logger.info("Transfert interne vérifié — Transaction ID : %s, montant : %s", tx_id, tx_amount)
                return result

        result["error"] = {"en": f"No internal transfer found matching ID={client_tx_id}.", "ar": f"لم يتم العثور على تحويل داخلي مطابق للمعرف={client_tx_id}."}.get(lang, f"Aucun transfert interne correspondant trouvé pour l'ID={client_tx_id}.")
        return result

    except (httpx.TimeoutException, TimeoutError):
        result["error"] = {"en": "Timeout connecting to Binance API.", "ar": "انتهت مهلة الاتصال بـ Binance API."}.get(lang, "Délai d'attente dépassé lors de la connexion à l'API Binance.")
        logger.exception(result["error"])
        return result
    except Exception as exc:
        result["error"] = f"Erreur inattendue lors de la vérification interne : {exc}"
        logger.exception(result["error"])
        return result
