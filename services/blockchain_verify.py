# services/blockchain_verify.py — Verify BEP20 USDT transactions on BNB Chain
# Queries public JSON-RPC nodes to check tx existence, status, contract, recipient and amount.

from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)

# BSC public JSON-RPC endpoints to query
BSC_RPC_NODES = [
    "https://bsc-dataseed.binance.org/",
    "https://bsc-dataseed1.defibit.io/",
    "https://rpc.ankr.com/bsc"
]

# USDT Contract Address on BNB Chain
USDT_CONTRACT_BSC = "0x55d398326f99059ff775485246999027b3197955"


async def verify_bep20_payment(
    tx_hash: str,
    expected_amount: float,
    merchant_address: str,
) -> dict:
    """Verifies a BEP20 USDT transfer on BNB Chain.

    Args:
        tx_hash: The transaction hash provided by the user.
        expected_amount: The expected payment amount in USD/USDT.
        merchant_address: The configured store wallet address to receive funds.

    Returns:
        dict: A dictionary with 'verified' (bool), 'transaction' (dict or None), and 'error' (str or None).
    """
    result = {"verified": False, "transaction": None, "error": None}

    # Clean transaction hash
    tx_hash = tx_hash.strip()
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        result["error"] = "Invalid transaction hash format. Must be 66 characters and start with 0x."
        return result

    # Clean merchant address
    merchant_address = merchant_address.strip().lower()
    if not merchant_address:
        result["error"] = "Merchant BEP20 wallet address is not configured."
        return result

    tx_data = None
    receipt_data = None
    rpc_error = None

    import asyncio

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Retry up to 4 times (max ~12 seconds) to allow network indexing
        for attempt in range(4):
            for node in BSC_RPC_NODES:
                try:
                    # Query transaction details
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionByHash",
                        "params": [tx_hash],
                        "id": 1
                    }
                    tx_resp = await client.post(node, json=tx_payload)
                    if tx_resp.status_code != 200:
                        continue
                    tx_res = tx_resp.json()
                    if "error" in tx_res or not tx_res.get("result"):
                        continue
                    tx_data = tx_res["result"]

                    # Query transaction receipt (to verify status)
                    receipt_payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                        "id": 2
                    }
                    receipt_resp = await client.post(node, json=receipt_payload)
                    if receipt_resp.status_code != 200:
                        continue
                    receipt_res = receipt_resp.json()
                    if "error" in receipt_res or not receipt_res.get("result"):
                        continue
                    receipt_data = receipt_res["result"]

                    break  # Successful fetch from this node
                except Exception as e:
                    rpc_error = str(e)
                    logger.warning("Error querying BSC node %s: %s", node, e)
                    continue
            
            if tx_data and receipt_data:
                break
            
            # Wait before next attempt
            if attempt < 3:
                await asyncio.sleep(3)

    if not tx_data or not receipt_data:
        result["error"] = f"Transaction not found on-chain. It might still be confirming. Please wait a few seconds and try again. (RPC error: {rpc_error})"
        return result

    # 1. Verify transaction status (0x1 = success)
    status = receipt_data.get("status")
    if status != "0x1" and status != 1:
        result["error"] = "Transaction failed on-chain."
        return result

    # 2. Verify target contract address is the USDT contract on BSC
    tx_to = (tx_data.get("to") or "").lower()
    if tx_to != USDT_CONTRACT_BSC.lower():
        result["error"] = f"Target contract is not BSC USDT. Transferred to: {tx_to}"
        return result

    # 3. Verify transfer function signature (transfer(address,uint256) -> 0xa9059cbb)
    tx_input = tx_data.get("input") or ""
    if not tx_input.lower().startswith("0xa9059cbb"):
        result["error"] = "Transaction is not a standard BEP20 transfer call."
        return result

    try:
        # transfer(address _to, uint256 _value) input decoding:
        # Method ID: 0xa9059cbb (10 characters: '0x' + 8 chars)
        # Recipient parameter starts at 10, length 64 chars
        # Recipient address is the last 40 chars
        to_param = tx_input[10:74]
        recipient_addr = "0x" + to_param[-40:].lower()

        if recipient_addr != merchant_address:
            result["error"] = f"Transfer recipient ({recipient_addr}) does not match merchant address ({merchant_address})."
            return result

        # Amount parameter starts at 74, length 64 chars
        value_param = tx_input[74:138]
        raw_value = int(value_param, 16)
        # Convert from 18 decimals
        value_usdt = raw_value / (10**18)

        # Allow small deviation (e.g. 0.01 USDT)
        if value_usdt < (expected_amount - 0.01):
            result["error"] = f"Insufficient transfer amount. Received: {value_usdt:.4f} USDT, expected: {expected_amount:.2f} USDT."
            return result

        result["verified"] = True
        result["transaction"] = {
            "tx_hash": tx_hash,
            "amount": value_usdt,
            "to": recipient_addr
        }
        return result

    except Exception as e:
        result["error"] = f"Failed to parse transaction input parameters: {e}"
        return result
