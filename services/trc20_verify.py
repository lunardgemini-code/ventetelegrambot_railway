# services/trc20_verify.py — Verify TRC20 USDT transactions on TRON Chain
# Queries TronGrid public API to check tx existence, success status, contract, recipient, and amount.

from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)

# TRON USDT Contract Address
USDT_CONTRACT_TRON = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
# Hexadecimal representation of the TRON USDT contract: 0x41 + 20-byte key hash
USDT_CONTRACT_TRON_HEX = "41a614f803b6fd780986a42c78ec9c7f77e6ded13c"

# Transfer(address,address,uint256) topic
TRANSFER_TOPIC = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_HTTP_CLIENT: httpx.AsyncClient | None = None


async def _get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=10.0)
    return _HTTP_CLIENT


def base58_to_hex(base58_str: str) -> str:
    """Decodes a Base58 check address to its hex representation (including prefix byte 0x41)."""
    num = 0
    for char in base58_str:
        num = num * 58 + BASE58_ALPHABET.index(char)
    hex_str = hex(num)[2:]
    if len(hex_str) % 2 != 0:
        hex_str = "0" + hex_str
    # Pad to 25 bytes (50 hex characters)
    hex_str = hex_str.zfill(50)
    # Return first 21 bytes (prefix + public key hash)
    return hex_str[:42]


async def verify_trc20_payment(
    tx_hash: str,
    expected_amount: float,
    merchant_address: str,
) -> dict:
    """Verifies a TRC20 USDT transfer on TRON Chain.

    Args:
        tx_hash: The transaction hash provided by the user.
        expected_amount: The expected payment amount in USD/USDT.
        merchant_address: The configured store wallet address (Base58) to receive funds.

    Returns:
        dict: A dictionary with 'verified' (bool), 'transaction' (dict or None), and 'error' (str or None).
    """
    result = {"verified": False, "transaction": None, "error": None}

    tx_hash = tx_hash.strip()
    if len(tx_hash) != 64:
        result["error"] = "Invalid TRC20 transaction hash format. Must be 64 characters hex."
        return result

    merchant_address = merchant_address.strip()
    if not merchant_address:
        result["error"] = "Merchant TRC20 wallet address is not configured."
        return result

    # Convert merchant Base58 address to hex format for comparison
    try:
        merchant_hex = base58_to_hex(merchant_address).lower()
    except Exception as e:
        result["error"] = f"Invalid merchant address format: {e}"
        return result

    tx_info = None
    rpc_error = None

    import asyncio

    # Connect to TronGrid API to fetch transaction receipt
    client = await _get_http_client()
    # Retry up to 4 times (max ~12 seconds) to allow network indexing
    for attempt in range(4):
        try:
            resp = await client.post(
                "https://api.trongrid.io/wallet/gettransactioninfobyid",
                json={"value": tx_hash},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                # If empty {} is returned, it means not found yet
                if data and "id" in data:
                    tx_info = data
                    break
        except Exception as e:
            rpc_error = str(e)
            logger.warning("Error querying TronGrid API: %s", e)
        
        # Wait before next attempt
        if attempt < 3:
            await asyncio.sleep(3)

    if not tx_info:
        result["error"] = f"Transaction not found on-chain. It might still be confirming. Please wait a few seconds and try again. (API error: {rpc_error})"
        return result

    # 1. Verify transaction status
    receipt = tx_info.get("receipt", {})
    
    # Check if receipt exists and is successful
    success = False
    if receipt and receipt.get("result") == "SUCCESS":
        success = True
    else:
        ret = tx_info.get("ret", [{}])
        if ret and len(ret) > 0 and ret[0].get("contractRet") == "SUCCESS":
            success = True
            
    if not success:
        result["error"] = "Transaction failed or reverted on TRON chain."
        return result

    # 2. Inspect logs to find the USDT Transfer event
    logs = tx_info.get("log", [])
    if not logs:
        result["error"] = "No transaction logs found (not a TRC20 contract call)."
        return result

    usdt_log_found = False
    for log in logs:
        log_address = (log.get("address") or "").lower()
        if log_address != USDT_CONTRACT_TRON_HEX.lower() and log_address != "41" + USDT_CONTRACT_TRON_HEX[2:].lower():
            continue

        topics = log.get("topics", [])
        if not topics or topics[0].lower() != TRANSFER_TOPIC.lower():
            continue

        if len(topics) < 3:
            continue

        # Extract recipient hex address (last 40 characters of topic 2, prepended with 41)
        recipient_hex_raw = topics[2][-40:].lower()
        recipient_hex = "41" + recipient_hex_raw

        if recipient_hex != merchant_hex:
            continue

        # Found the matching log! Now parse the amount in data
        usdt_log_found = True
        try:
            data_hex = log.get("data") or "0"
            raw_value = int(data_hex, 16)
            # USDT on TRON has 6 decimals
            value_usdt = raw_value / (10**6)

            # Check if amount is sufficient (allow 0.01 USDT deviation)
            if value_usdt < (expected_amount - 0.01):
                result["error"] = f"Insufficient TRC20 amount. Received: {value_usdt:.2f} USDT, expected: {expected_amount:.2f} USDT."
                return result

            result["verified"] = True
            result["transaction"] = {
                "tx_hash": tx_hash,
                "amount": value_usdt,
                "to": merchant_address
            }
            return result

        except Exception as e:
            result["error"] = f"Failed to parse TRC20 transfer value: {e}"
            return result

    if not usdt_log_found:
        result["error"] = f"USDT transfer to merchant address {merchant_address} not found in transaction logs."
        
    return result
