# services/binance_verify.py — Vérification des paiements Binance Pay
# Utilise l'API SAPI de Binance pour consulter l'historique des transactions.

from __future__ import annotations

import hashlib
import hmac
import logging
import time

import httpx

from config import BINANCE_API_KEY, BINANCE_API_SECRET

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────
BASE_URL = "https://api.binance.com/sapi/v1/pay/transactions"
RECV_WINDOW = 5000
# Tolérance de comparaison des montants (en USD)
AMOUNT_TOLERANCE = 0.01
# Fenêtre de recherche des transactions (en millisecondes) : 2 heures
SEARCH_WINDOW_MS = 2 * 60 * 60 * 1000


def _generate_signature(query_string: str, secret: str) -> str:
    """Génère la signature HMAC-SHA256 pour l'API Binance."""
    return hmac.new(
        secret.encode(),
        query_string.encode(),
        hashlib.sha256,
    ).hexdigest()


async def verify_payment(
    client_order_id: str,
    expected_amount: float,
    api_key: str | None = None,
    api_secret: str | None = None,
) -> dict:
    """Vérifie un paiement Binance Pay en consultant l'historique des transactions."""
    result: dict = {"verified": False, "transaction": None, "error": None}

    key_to_use = api_key if api_key else BINANCE_API_KEY
    secret_to_use = api_secret if api_secret else BINANCE_API_SECRET

    if not key_to_use or not secret_to_use:
        result["error"] = "Clés API Binance non configurées."
        logger.error(result["error"])
        return result

    now_ms = int(time.time() * 1000)
    start_ts = now_ms - SEARCH_WINDOW_MS

    # Construire la query string avec les paramètres triés
    query_string = (
        f"timestamp={now_ms}"
        f"&recvWindow={RECV_WINDOW}"
        f"&startTimestamp={start_ts}"
        f"&endTimestamp={now_ms}"
    )
    signature = _generate_signature(query_string, secret_to_use)
    full_url = f"{BASE_URL}?{query_string}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": key_to_use,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(full_url, headers=headers)

        # Vérifier le code HTTP
        if response.status_code != 200:
            result["error"] = (
                f"Erreur API Binance — HTTP {response.status_code} : "
                f"{response.text[:200]}"
            )
            logger.error(result["error"])
            return result

        data = response.json()

        # L'API retourne {"code": "000000", "data": [...]} en cas de succès
        if data.get("code") != "000000":
            result["error"] = (
                f"Erreur API Binance — code {data.get('code')} : "
                f"{data.get('message', 'Erreur inconnue')}"
            )
            logger.error(result["error"])
            return result

        transactions: list[dict] = data.get("data", [])

        if not transactions:
            result["error"] = "Aucune transaction trouvée dans la période."
            return result

        # Parcourir les transactions pour trouver une correspondance
        for tx in transactions:
            tx_amount = float(tx.get("amount", 0))
            tx_id = str(tx.get("transactionId", ""))
            tx_order_id = str(tx.get("orderId", ""))
            tx_order_type = str(tx.get("orderType", "")).upper()

            # Vérifier que c'est une réception / transfert entrant
            # Les types courants : C2C, PAY, CRYPTO_BOX, etc.
            is_incoming = tx_order_type in (
                "C2C",
                "PAY",
                "CRYPTO_BOX",
                "TRANSFER",
                "1",  # Certaines versions de l'API utilisent des codes numériques
            )

            # Correspondance par identifiant (exacte)
            cleaned_client_id = client_order_id.strip().upper()
            id_match = (
                cleaned_client_id == tx_id.upper()
                or cleaned_client_id == tx_order_id.upper()
            )

            # Correspondance par montant (avec tolérance)
            amount_match = abs(tx_amount - expected_amount) <= AMOUNT_TOLERANCE

            if id_match and is_incoming and amount_match:
                result["verified"] = True
                result["transaction"] = tx
                logger.info(
                    "Paiement vérifié — Transaction ID : %s, montant : %s",
                    tx_id,
                    tx_amount,
                )
                return result

        # Aucune correspondance trouvée
        result["error"] = (
            "Aucune transaction correspondante trouvée. "
            f"Recherché : ID={client_order_id}, montant={expected_amount}"
        )
        return result

    except httpx.TimeoutException:
        result["error"] = "Délai d'attente dépassé lors de la connexion à l'API Binance."
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
