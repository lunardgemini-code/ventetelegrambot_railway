"""Lightweight catalog analysis and strict multi-supplier search."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import secrets
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Awaitable, Callable

import httpx

from database.jobs import (
    claim_next_background_job,
    complete_background_job,
    create_background_job_unless_active,
    fail_background_job,
    get_latest_background_job_by_type,
    update_background_job_progress,
)
from database.supplier_ai import (
    get_supplier_ai_index_status,
    get_supplier_wallet_snapshots,
    list_indexed_supplier_products,
    list_supplier_products_for_analysis,
    save_supplier_ai_run_summary,
    upsert_supplier_product_analysis,
)
from database.suppliers import get_supplier_dashboard_summaries
from services.supplier_registry import (
    is_supplier_configured,
    list_supplier_providers,
)
from services.supplier_router import _ascii, extract_product_signature
from services.supplier_sync import sync_supplier_catalog


SUPPLIER_AI_JOB_TYPE = "supplier_ai_sync"
_POLL_SECONDS = 2.0
_DELIVERY_MODES = {"account", "activation", "unknown"}
_ACCESS_MODES = {"private", "shared", "unknown"}


def _configured_providers() -> list[dict]:
    return [
        provider for provider in list_supplier_providers()
        if is_supplier_configured(str(provider["code"]))
    ]


def _source_hash(product: dict) -> str:
    payload = {
        "name": str(product.get("name") or ""),
        "description": str(product.get("description") or "")[:1500],
        "warranty_days": int(product.get("warranty_days") or 0),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _region(text: str) -> str:
    normalized = _ascii(text)
    for pattern, value in (
        (r"\b(?:usa|us only|united states)\b", "US"),
        (r"\b(?:uk|united kingdom)\b", "UK"),
        (r"\b(?:eu|europe)\b", "EU"),
        (r"\b(?:india|indian)\b", "IN"),
        (r"\b(?:turkey|turkiye)\b", "TR"),
        (r"\bglobal\b", "GLOBAL"),
    ):
        if re.search(pattern, normalized):
            return value
    return ""


def _deterministic_analysis(product: dict) -> dict:
    name = str(product.get("name") or "")
    description = str(product.get("description") or "")
    signature = extract_product_signature(name, description)
    known = sum(bool(signature.get(key)) for key in (
        "family", "duration_months", "duration_days"
    ))
    known += signature["delivery_mode"] != "unknown"
    known += signature["access"] != "unknown"
    return {
        "supplier_product_id": int(product["id"]),
        "supplier_code": str(product["supplier_code"]),
        "family": str(signature.get("family") or ""),
        "duration_months": signature.get("duration_months"),
        "duration_days": signature.get("duration_days"),
        "delivery_mode": str(signature.get("delivery_mode") or "unknown"),
        "access_mode": str(signature.get("access") or "unknown"),
        "region": _region(f"{name} {description}"),
        "tokens": signature.get("tokens") or [],
        "analysis_source": "deterministic",
        "confidence": min(0.98, 0.45 + known * 0.10),
        "source_hash": _source_hash(product),
    }


async def _gemini_analyze_batch(products: list[dict]) -> dict[int, dict]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or not products:
        return {}
    model = os.environ.get("GEMINI_CATALOG_MODEL", "gemini-2.5-flash").strip()
    safe_products = [
        {
            "id": int(product["id"]),
            "name": str(product.get("name") or "")[:300],
            "description": str(product.get("description") or "")[:700],
        }
        for product in products
    ]
    prompt = (
        "Classify digital product supplier listings. Return JSON only with this schema: "
        "{\"products\":[{\"id\":1,\"family\":\"grok\",\"duration_months\":1,"
        "\"duration_days\":null,\"delivery_mode\":\"account|activation|unknown\","
        "\"access_mode\":\"private|shared|unknown\",\"region\":\"GLOBAL\","
        "\"confidence\":0.9}]}. Never invent a duration or access mode. A missing fact must "
        "be null, empty, or unknown. Do not analyze prices, warranties, credentials, or customer data. Listings:\n"
        + json.dumps(safe_products, ensure_ascii=False)
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                json=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.I).strip())
            return {
                int(item["id"]): item
                for item in data.get("products", [])
                if isinstance(item, dict) and str(item.get("id", "")).isdigit()
            }
    except Exception:
        return {}


def _merge_ai(analysis: dict, suggestion: dict | None) -> dict:
    if not suggestion:
        return analysis
    merged = dict(analysis)
    family = re.sub(r"[^a-z0-9_-]+", "", _ascii(suggestion.get("family") or ""))[:40]
    if not merged["family"] and family:
        merged["family"] = family
    for key in ("duration_months", "duration_days"):
        if merged.get(key) is None:
            try:
                value = int(suggestion.get(key))
                if 0 < value <= (120 if key == "duration_months" else 4000):
                    merged[key] = value
            except (TypeError, ValueError):
                pass
    delivery = str(suggestion.get("delivery_mode") or "unknown").lower()
    access = str(suggestion.get("access_mode") or "unknown").lower()
    if merged["delivery_mode"] == "unknown" and delivery in _DELIVERY_MODES:
        merged["delivery_mode"] = delivery
    if merged["access_mode"] == "unknown" and access in _ACCESS_MODES:
        merged["access_mode"] = access
    if not merged["region"]:
        merged["region"] = re.sub(r"[^A-Za-z0-9_-]+", "", str(suggestion.get("region") or ""))[:40].upper()
    try:
        ai_confidence = min(1.0, max(0.0, float(suggestion.get("confidence") or 0)))
    except (TypeError, ValueError):
        ai_confidence = 0.0
    merged["confidence"] = max(float(merged["confidence"]), ai_confidence)
    merged["analysis_source"] = "gemini"
    return merged


async def analyze_supplier_catalog(
    *,
    use_ai: bool = True,
    heartbeat: Callable[[int, int], Awaitable[None]] | None = None,
) -> dict:
    providers = _configured_providers()
    codes = [str(provider["code"]) for provider in providers]
    products = await list_supplier_products_for_analysis(codes)
    changed = [product for product in products if _source_hash(product) != product.get("indexed_source_hash")]
    analyses = {int(product["id"]): _deterministic_analysis(product) for product in changed}
    ai_reviewed = 0
    ai_used = 0
    try:
        max_ai = max(0, min(int(os.environ.get("GEMINI_CATALOG_MAX_PRODUCTS", "80")), 300))
    except (TypeError, ValueError):
        max_ai = 80
    ambiguous = [
        product for product in changed
        if not analyses[int(product["id"])]["family"]
        or analyses[int(product["id"])]["duration_months"] is None
        and analyses[int(product["id"])]["duration_days"] is None
    ][:max_ai]
    if use_ai and os.environ.get("GEMINI_API_KEY", "").strip():
        for start in range(0, len(ambiguous), 20):
            batch = ambiguous[start:start + 20]
            suggestions = await _gemini_analyze_batch(batch)
            ai_reviewed += len(batch)
            for product in batch:
                product_id = int(product["id"])
                before = analyses[product_id]
                analyses[product_id] = _merge_ai(before, suggestions.get(product_id))
                if analyses[product_id]["analysis_source"] == "gemini":
                    ai_used += 1
            if heartbeat:
                await heartbeat(ai_reviewed, len(ambiguous))
    saved = await upsert_supplier_product_analysis(list(analyses.values()))
    return {
        "total": len(products),
        "changed": len(changed),
        "reused": max(0, len(products) - len(changed)),
        "indexed": saved,
        "ai_reviewed": ai_reviewed,
        "ai_used": ai_used,
    }


def _parse_datetime(value) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


async def _provider_metadata() -> tuple[list[dict], dict[str, dict]]:
    providers = _configured_providers()
    summaries = await get_supplier_dashboard_summaries([str(item["code"]) for item in providers])
    detected_counts = Counter(
        str(value.get("detected_name") or "").strip().casefold()
        for value in summaries.values() if str(value.get("detected_name") or "").strip()
    )
    metadata = {}
    for provider in providers:
        code = str(provider["code"])
        summary = summaries.get(code, {})
        custom = str(summary.get("display_name") or "").strip()
        detected = str(summary.get("detected_name") or "").strip()
        unique_detected = detected if detected and detected_counts[detected.casefold()] == 1 else ""
        metadata[code] = {
            "name": custom or unique_detected or str(provider.get("name") or code),
            "enabled": bool(summary.get("enabled")),
            "last_sync": summary.get("last_sync") or "",
        }
    return providers, metadata


async def search_supplier_catalog(filters: dict) -> dict:
    query = " ".join(str(filters.get("query") or "").split())[:120]
    if not query:
        raise ValueError("SEARCH_QUERY_REQUIRED")
    providers, metadata = await _provider_metadata()
    codes = [str(provider["code"]) for provider in providers]
    rows, wallets = await asyncio.gather(
        list_indexed_supplier_products(codes),
        get_supplier_wallet_snapshots(codes),
    )
    query_signature = extract_product_signature(query)
    try:
        duration_value = int(filters.get("duration_value") or 0)
    except (TypeError, ValueError):
        raise ValueError("INVALID_DURATION")
    duration_unit = str(filters.get("duration_unit") or "months").lower()
    requested_months = query_signature.get("duration_months")
    requested_days = query_signature.get("duration_days")
    if duration_value > 0:
        if duration_unit == "years":
            requested_months, requested_days = duration_value * 12, None
        elif duration_unit == "days":
            requested_months, requested_days = None, duration_value
        else:
            requested_months, requested_days = duration_value, None
    try:
        min_warranty = max(0, int(filters.get("min_warranty_days") or 0))
        max_price = max(0.0, float(filters.get("max_price") or 0))
        limit = min(50, max(1, int(filters.get("limit") or 25)))
    except (TypeError, ValueError):
        raise ValueError("INVALID_SEARCH_FILTER")
    normalized_query = _ascii(query)
    require_warranty = bool(filters.get("require_warranty")) or any(
        term in normalized_query for term in ("warranty", "garantie")
    )
    if require_warranty and min_warranty <= 0:
        min_warranty = 1
    full_warranty = any(term in normalized_query for term in (
        "full warranty", "warranty full", "garantie complete", "garantie totale"
    ))
    if full_warranty:
        if requested_days is not None:
            min_warranty = max(min_warranty, int(requested_days))
        elif requested_months is not None:
            min_warranty = max(min_warranty, int(requested_months) * 30)
    delivery = str(filters.get("delivery_mode") or query_signature.get("delivery_mode") or "unknown").lower()
    access = str(filters.get("access_mode") or query_signature.get("access") or "unknown").lower()
    if delivery not in _DELIVERY_MODES or access not in _ACCESS_MODES:
        raise ValueError("INVALID_SEARCH_FILTER")
    include_unfunded = bool(filters.get("include_unfunded"))
    now = datetime.now(timezone.utc)
    results = []
    for row in rows:
        code = str(row["supplier_code"])
        price = max(0.0, float(row.get("base_price") or 0))
        stock = max(0, int(row.get("remote_stock") or 0))
        if price <= 0 or stock <= 0 or max_price and price > max_price:
            continue
        if query_signature.get("family") and row.get("family") != query_signature["family"]:
            continue
        if requested_months is not None and int(row.get("duration_months") or 0) != int(requested_months):
            continue
        if requested_days is not None and int(row.get("duration_days") or 0) != int(requested_days):
            continue
        warranty = max(0, int(row.get("warranty_days") or 0))
        if warranty < min_warranty:
            continue
        if delivery != "unknown" and row.get("delivery_mode") != delivery:
            continue
        if access != "unknown" and row.get("access_mode") != access:
            continue
        tokens = set(str(token) for token in row.get("tokens") or [])
        query_tokens = set(query_signature.get("tokens") or [])
        token_score = len(tokens & query_tokens) / len(tokens | query_tokens) if tokens | query_tokens else 0.0
        name_score = SequenceMatcher(None, normalized_query, _ascii(row.get("name") or "")).ratio()
        similarity = max(token_score, name_score)
        if not query_signature.get("family") and similarity < 0.28:
            continue
        balance = float(wallets.get(code, {}).get("balance") or 0)
        affordable = min(stock, int(math.floor((balance + 1e-9) / price)))
        if not include_unfunded and affordable <= 0:
            continue
        completed = max(0, int(row.get("completed_orders") or 0))
        failed = max(0, int(row.get("failed_orders") or 0))
        unknown = max(0, int(row.get("unknown_orders") or 0))
        reliability = (completed + 9.0) / (completed + failed + unknown + 10.0)
        synced_at = _parse_datetime(row.get("last_synced_at"))
        age_hours = max(0.0, (now - synced_at).total_seconds() / 3600) if synced_at else 9999.0
        stale_penalty = min(0.20, age_hours / 720.0)
        route_score = price * (1.0 + (1.0 - reliability) * 0.10 + stale_penalty)
        reasons = [f"conforme aux filtres", f"fiabilite {round(reliability * 100)}%"]
        if affordable > 0:
            reasons.append(f"{affordable} achetable(s)")
        elif include_unfunded:
            reasons.append("wallet insuffisant")
        results.append({
            "supplier_product_id": int(row["id"]),
            "supplier_code": code,
            "supplier_name": metadata.get(code, {}).get("name", code),
            "supplier_enabled": bool(metadata.get(code, {}).get("enabled")),
            "external_product_id": str(row.get("external_product_id") or ""),
            "name": str(row.get("name") or ""),
            "price": round(price, 4),
            "remote_stock": stock,
            "affordable_stock": affordable,
            "wallet_balance": round(balance, 2),
            "warranty_days": warranty,
            "duration_months": row.get("duration_months"),
            "duration_days": row.get("duration_days"),
            "delivery_mode": row.get("delivery_mode") or "unknown",
            "access_mode": row.get("access_mode") or "unknown",
            "region": row.get("region") or "",
            "reliability": round(reliability, 4),
            "freshness_hours": round(age_hours, 1),
            "confidence": round(float(row.get("confidence") or 0), 4),
            "route_score": round(route_score, 6),
            "reason": " · ".join(reasons),
        })
    results.sort(key=lambda item: (
        item["affordable_stock"] <= 0,
        item["route_score"],
        -item["reliability"],
        item["supplier_name"].casefold(),
    ))
    return {
        "query": query,
        "intent": {
            "family": query_signature.get("family") or "",
            "duration_months": requested_months,
            "duration_days": requested_days,
            "min_warranty_days": min_warranty,
            "full_warranty": full_warranty,
            "delivery_mode": delivery,
            "access_mode": access,
            "include_unfunded": include_unfunded,
        },
        "count": min(len(results), limit),
        "results": results[:limit],
    }


def _public_job(job: dict | None) -> dict | None:
    if not job:
        return None
    return {
        "job_id": job.get("id"),
        "status": job.get("status"),
        "done": int(job.get("progress_done") or 0),
        "failed": int(job.get("progress_failed") or 0),
        "total": int(job.get("progress_total") or 0),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "completed_at": job.get("completed_at"),
    }


async def enqueue_supplier_ai_sync(*, use_ai: bool = True) -> tuple[dict, bool]:
    codes = [str(provider["code"]) for provider in _configured_providers()]
    if not codes:
        raise ValueError("NO_CONFIGURED_SUPPLIERS")
    job, created = await create_background_job_unless_active(
        secrets.token_urlsafe(12),
        SUPPLIER_AI_JOB_TYPE,
        {"supplier_codes": codes, "use_ai": bool(use_ai)},
        max_attempts=3,
        progress_total=len(codes) + 1,
    )
    return _public_job(job) or {}, created


async def get_supplier_ai_status() -> dict:
    providers = _configured_providers()
    index, job = await asyncio.gather(
        get_supplier_ai_index_status(),
        get_latest_background_job_by_type(SUPPLIER_AI_JOB_TYPE),
    )
    return {
        **index,
        "configured_suppliers": len(providers),
        "job": _public_job(job),
    }


async def _run_supplier_ai_job(job: dict) -> None:
    job_id = str(job["id"])
    payload = job.get("payload") or {}
    codes = [str(code) for code in payload.get("supplier_codes") or []]
    total = len(codes) + 1
    cursor = min(len(codes), max(0, int(job.get("cursor_value") or 0)))
    done = max(0, int(job.get("progress_done") or 0))
    failed = max(0, int(job.get("progress_failed") or 0))
    provider_results = []
    for index in range(cursor, len(codes)):
        code = codes[index]
        try:
            result = await sync_supplier_catalog(
                code,
                min_interval_seconds=0,
                refresh_balance=True,
                refresh_disabled=True,
            )
            done += 1
            provider_results.append({"supplier_code": code, "status": result.get("status"), "products": int(result.get("synced") or 0)})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failed += 1
            provider_results.append({"supplier_code": code, "status": "failed", "error": str(exc)[:160]})
        await update_background_job_progress(
            job_id,
            done=done,
            failed=failed,
            total=total,
            cursor_value=index + 1,
        )

    async def heartbeat(_reviewed: int, _total_ai: int) -> None:
        await update_background_job_progress(
            job_id,
            done=done,
            failed=failed,
            total=total,
            cursor_value=len(codes),
        )

    analysis = await analyze_supplier_catalog(
        use_ai=bool(payload.get("use_ai", True)),
        heartbeat=heartbeat,
    )
    summary = {"providers": provider_results, "analysis": analysis}
    await save_supplier_ai_run_summary(summary)
    await complete_background_job(
        job_id,
        done=done + 1,
        failed=failed,
        total=total,
        cursor_value=total,
    )


async def supplier_ai_job_worker() -> None:
    while True:
        try:
            job = await claim_next_background_job(job_types={SUPPLIER_AI_JOB_TYPE})
            if not job:
                await asyncio.sleep(_POLL_SECONDS)
                continue
            try:
                await _run_supplier_ai_job(job)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await fail_background_job(
                    str(job["id"]),
                    str(exc),
                    retry_delay_seconds=min(120, 15 * max(1, int(job.get("attempts") or 1))),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5.0)


__all__ = [
    "SUPPLIER_AI_JOB_TYPE",
    "analyze_supplier_catalog",
    "enqueue_supplier_ai_sync",
    "get_supplier_ai_status",
    "search_supplier_catalog",
    "supplier_ai_job_worker",
]
