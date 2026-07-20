"""Lightweight catalog analysis and strict multi-supplier search."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
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
SUPPLIER_AI_ANALYZE_JOB_TYPE = "supplier_ai_analyze"
logger = logging.getLogger(__name__)
_POLL_SECONDS = 2.0
_DELIVERY_MODES = {"account", "activation", "unknown"}
_ACCESS_MODES = {"private", "shared", "unknown"}
_GROUP_GENERIC_TOKENS = {
    "account", "accounts", "activation", "activate", "active", "ready",
    "email", "password", "private", "shared", "full", "warranty", "fw",
    "guarantee", "garantie", "complete", "month", "months", "mois", "day",
    "days", "jour", "jours", "year", "years", "ans", "global", "renewable",
    "renew", "new", "old", "user", "users", "subscription", "plan", "with",
    "and", "the", "for", "your", "own", "provided", "compte", "prive",
    "partage", "lifetime", "stock", "instant", "delivery",
}
_GROUP_FAMILY_TOKENS = {
    "chatgpt": {"chatgpt", "chat", "gpt", "openai"},
    "gemini": {"gemini", "google", "googleone"},
    "capcut": {"capcut"},
    "coursera": {"coursera"},
    "lovable": {"lovable"},
    "grok": {"grok", "xai"},
    "nordvpn": {"nord", "nordvpn", "vpn"},
    "youtube": {"youtube", "yt"},
    "linkedin": {"linkedin"},
    "replit": {"replit"},
    "elevenlabs": {"elevenlabs"},
    "office365": {"office", "office365", "microsoft", "365"},
}


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
    configured_model = os.environ.get("GEMINI_CATALOG_MODEL", "").strip()
    models = list(dict.fromkeys(filter(None, (
        configured_model,
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
    ))))
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
    async with httpx.AsyncClient(timeout=35) as client:
        for index, model in enumerate(models):
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    json=payload,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                )
                if response.status_code == 404 and index + 1 < len(models):
                    logger.warning("Gemini catalog model %s is unavailable; trying fallback", model)
                    continue
                response.raise_for_status()
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.I).strip())
                return {
                    int(item["id"]): item
                    for item in data.get("products", [])
                    if isinstance(item, dict) and str(item.get("id", "")).isdigit()
                }
            except Exception as exc:
                logger.warning("Gemini catalog analysis failed with model %s: %s", model, str(exc)[:180])
                if index + 1 >= len(models):
                    break
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
    force: bool = False,
    heartbeat: Callable[[int, int], Awaitable[None]] | None = None,
) -> dict:
    providers = _configured_providers()
    codes = [str(provider["code"]) for provider in providers]
    products = await list_supplier_products_for_analysis(codes)
    changed = [
        product for product in products
        if force or _source_hash(product) != product.get("indexed_source_hash")
    ]
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
        "forced": bool(force),
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
            min_warranty = max(min_warranty, int(math.ceil(int(requested_days) * 0.80)))
        elif requested_months is not None:
            min_warranty = max(min_warranty, int(math.ceil(int(requested_months) * 30 * 0.80)))
    delivery = str(filters.get("delivery_mode") or query_signature.get("delivery_mode") or "unknown").lower()
    access = str(filters.get("access_mode") or query_signature.get("access") or "unknown").lower()
    if delivery not in _DELIVERY_MODES or access not in _ACCESS_MODES:
        raise ValueError("INVALID_SEARCH_FILTER")
    include_unfunded = bool(filters.get("include_unfunded"))
    now = datetime.now(timezone.utc)
    results = []
    hidden_unfunded_count = 0
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
            hidden_unfunded_count += 1
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
        "hidden_unfunded_count": hidden_unfunded_count,
        "results": results[:limit],
    }


def _group_variant_tokens(name: str, family: str) -> tuple[str, ...]:
    tokens = set(re.findall(r"[a-z0-9]+", _ascii(name)))
    tokens.difference_update(_GROUP_GENERIC_TOKENS)
    tokens.difference_update(_GROUP_FAMILY_TOKENS.get(family, {family}))
    tokens = {
        token for token in tokens
        if not token.isdigit()
        and not re.fullmatch(r"\d+(?:m|mo|mos|month|months|d|day|days|y|yr|yrs|year|years)", token)
    }
    return tuple(sorted(tokens)[:10])


def _warranty_group(warranty_days: int, duration_months, duration_days) -> tuple[str, str]:
    if warranty_days <= 0:
        return "none", "Sans garantie"
    total_days = 0
    if duration_days:
        total_days = max(0, int(duration_days))
    elif duration_months:
        total_days = max(0, int(duration_months) * 30)
    if total_days and warranty_days >= math.ceil(total_days * 0.80):
        return "full", "Garantie complete"
    return f"limited:{warranty_days}", f"Garantie {warranty_days} j"


def _group_duration_label(duration_months, duration_days) -> str:
    if duration_months:
        return f"{int(duration_months)} mois"
    if duration_days:
        return f"{int(duration_days)} jours"
    return "Duree inconnue"


async def list_supplier_product_groups() -> dict:
    providers, metadata = await _provider_metadata()
    codes = [str(provider["code"]) for provider in providers]
    rows, wallets = await asyncio.gather(
        list_indexed_supplier_products(codes),
        get_supplier_wallet_snapshots(codes),
    )
    now = datetime.now(timezone.utc)
    grouped: dict[tuple, dict] = {}
    available_products = 0
    for row in rows:
        price = max(0.0, float(row.get("base_price") or 0))
        stock = max(0, int(row.get("remote_stock") or 0))
        if price <= 0 or stock <= 0:
            continue
        available_products += 1
        family = str(row.get("family") or "").strip().lower()
        months = int(row["duration_months"]) if row.get("duration_months") else None
        days = int(row["duration_days"]) if row.get("duration_days") else None
        delivery = str(row.get("delivery_mode") or "unknown")
        access = str(row.get("access_mode") or "unknown")
        region = str(row.get("region") or "").upper()
        warranty_days = max(0, int(row.get("warranty_days") or 0))
        warranty_key, warranty_label = _warranty_group(warranty_days, months, days)
        variants = _group_variant_tokens(str(row.get("name") or ""), family)
        comparable = bool(family and (months or days))
        if comparable:
            group_key = (family, variants, months, days, warranty_key, delivery, access, region)
        else:
            group_key = ("unclassified", int(row["id"]))
        if group_key not in grouped:
            family_label = family.replace("_", " ").replace("-", " ").title() if family else str(row.get("name") or "Produit non classe")
            if variants:
                family_label = f"{family_label} {' '.join(variants).title()}"
            qualifiers = [_group_duration_label(months, days), warranty_label]
            if delivery != "unknown":
                qualifiers.append("Activation" if delivery == "activation" else "Compte fourni")
            if access != "unknown":
                qualifiers.append("Prive" if access == "private" else "Partage")
            if region:
                qualifiers.append(region)
            grouped[group_key] = {
                "family": family,
                "variants": list(variants),
                "label": family_label,
                "signature": " - ".join(qualifiers),
                "duration_months": months,
                "duration_days": days,
                "warranty_kind": warranty_key,
                "warranty_label": warranty_label,
                "delivery_mode": delivery,
                "access_mode": access,
                "region": region,
                "comparable": comparable,
                "offers": [],
            }
        code = str(row["supplier_code"])
        balance = max(0.0, float(wallets.get(code, {}).get("balance") or 0))
        affordable = min(stock, int(math.floor((balance + 1e-9) / price)))
        completed = max(0, int(row.get("completed_orders") or 0))
        failed = max(0, int(row.get("failed_orders") or 0))
        unknown = max(0, int(row.get("unknown_orders") or 0))
        reliability = (completed + 9.0) / (completed + failed + unknown + 10.0)
        synced_at = _parse_datetime(row.get("last_synced_at"))
        age_hours = max(0.0, (now - synced_at).total_seconds() / 3600) if synced_at else 9999.0
        grouped[group_key]["offers"].append({
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
            "warranty_days": warranty_days,
            "reliability": round(reliability, 4),
            "confidence": round(float(row.get("confidence") or 0), 4),
            "freshness_hours": round(age_hours, 1),
        })
    groups = []
    for index, group in enumerate(grouped.values(), start=1):
        offers = group["offers"]
        offers.sort(key=lambda offer: (
            offer["price"],
            -offer["reliability"],
            offer["supplier_name"].casefold(),
        ))
        best_price = offers[0]["price"]
        highest_price = max(offer["price"] for offer in offers)
        groups.append({
            **group,
            "group_id": f"group-{index}",
            "offer_count": len(offers),
            "best_price": best_price,
            "highest_price": highest_price,
            "max_saving": round(max(0.0, highest_price - best_price), 4),
        })
    groups.sort(key=lambda group: (
        not group["comparable"],
        -group["offer_count"],
        group["best_price"],
        group["label"].casefold(),
    ))
    return {
        "group_count": len(groups),
        "available_products": available_products,
        "comparison_groups": sum(1 for group in groups if group["offer_count"] > 1),
        "groups": groups,
    }


def _public_job(job: dict | None) -> dict | None:
    if not job:
        return None
    return {
        "job_id": job.get("id"),
        "kind": "analysis" if job.get("job_type") == SUPPLIER_AI_ANALYZE_JOB_TYPE else "sync",
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
    analysis_job = await get_latest_background_job_by_type(SUPPLIER_AI_ANALYZE_JOB_TYPE)
    if analysis_job and analysis_job.get("status") in {"queued", "running"}:
        raise ValueError("SUPPLIER_ANALYSIS_IN_PROGRESS")
    job, created = await create_background_job_unless_active(
        secrets.token_urlsafe(12),
        SUPPLIER_AI_JOB_TYPE,
        {"supplier_codes": codes},
        max_attempts=3,
        progress_total=len(codes),
    )
    return _public_job(job) or {}, created


async def enqueue_supplier_ai_analysis(*, use_ai: bool = True) -> tuple[dict, bool]:
    if not _configured_providers():
        raise ValueError("NO_CONFIGURED_SUPPLIERS")
    sync_job = await get_latest_background_job_by_type(SUPPLIER_AI_JOB_TYPE)
    if sync_job and sync_job.get("status") in {"queued", "running"}:
        raise ValueError("SUPPLIER_SYNC_IN_PROGRESS")
    job, created = await create_background_job_unless_active(
        secrets.token_urlsafe(12),
        SUPPLIER_AI_ANALYZE_JOB_TYPE,
        {"use_ai": bool(use_ai), "force": True},
        max_attempts=3,
        progress_total=1,
    )
    return _public_job(job) or {}, created


async def get_supplier_ai_status() -> dict:
    providers = _configured_providers()
    index, sync_job, analysis_job = await asyncio.gather(
        get_supplier_ai_index_status(),
        get_latest_background_job_by_type(SUPPLIER_AI_JOB_TYPE),
        get_latest_background_job_by_type(SUPPLIER_AI_ANALYZE_JOB_TYPE),
    )
    jobs = [job for job in (sync_job, analysis_job) if job]
    active_jobs = [job for job in jobs if job.get("status") in {"queued", "running"}]
    latest_job = max(active_jobs or jobs, key=lambda job: str(job.get("created_at") or ""), default=None)
    return {
        **index,
        "configured_suppliers": len(providers),
        "job": _public_job(latest_job),
        "sync_job": _public_job(sync_job),
        "analysis_job": _public_job(analysis_job),
    }


async def _run_supplier_ai_job(job: dict) -> None:
    job_id = str(job["id"])
    payload = job.get("payload") or {}
    codes = [str(code) for code in payload.get("supplier_codes") or []]
    total = len(codes)
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

    await complete_background_job(
        job_id,
        done=done,
        failed=failed,
        total=total,
        cursor_value=total,
    )


async def _run_supplier_ai_analysis_job(job: dict) -> None:
    job_id = str(job["id"])
    payload = job.get("payload") or {}

    async def heartbeat(_reviewed: int, _total_ai: int) -> None:
        try:
            await update_background_job_progress(
                job_id,
                done=0,
                failed=0,
                total=1,
                cursor_value=0,
            )
        except Exception as exc:
            logger.warning("Supplier AI progress heartbeat failed: %s", str(exc)[:180])

    analysis = await analyze_supplier_catalog(
        use_ai=bool(payload.get("use_ai", True)),
        force=bool(payload.get("force", True)),
        heartbeat=heartbeat,
    )
    await save_supplier_ai_run_summary({"analysis": analysis})
    await complete_background_job(
        job_id,
        done=1,
        failed=0,
        total=1,
        cursor_value=1,
    )


async def supplier_ai_job_worker() -> None:
    while True:
        try:
            job = await claim_next_background_job(job_types={
                SUPPLIER_AI_JOB_TYPE,
                SUPPLIER_AI_ANALYZE_JOB_TYPE,
            })
            if not job:
                await asyncio.sleep(_POLL_SECONDS)
                continue
            try:
                if job.get("job_type") == SUPPLIER_AI_ANALYZE_JOB_TYPE:
                    await _run_supplier_ai_analysis_job(job)
                else:
                    await _run_supplier_ai_job(job)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "Supplier AI job %s (%s) failed on attempt %s",
                    job.get("id"),
                    job.get("job_type"),
                    job.get("attempts"),
                    exc_info=True,
                )
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
    "SUPPLIER_AI_ANALYZE_JOB_TYPE",
    "SUPPLIER_AI_JOB_TYPE",
    "analyze_supplier_catalog",
    "enqueue_supplier_ai_analysis",
    "enqueue_supplier_ai_sync",
    "get_supplier_ai_status",
    "list_supplier_product_groups",
    "search_supplier_catalog",
    "supplier_ai_job_worker",
]
