"""Product matching and deterministic routing across supplier accounts."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

import httpx


_STOP_WORDS = {
    "account", "accounts", "acc", "the", "and", "with", "for", "full",
    "warranty", "garantie", "complete", "complet", "no", "new", "ready",
    "made", "premium", "pro", "plan", "mois", "jour", "jours", "ans",
}
_ALIASES = {
    "chatgpt": "chatgpt", "chat": "chatgpt", "gpt": "chatgpt",
    "gemini": "gemini", "googleone": "gemini", "google": "gemini",
    "capcut": "capcut", "coursera": "coursera", "lovable": "lovable",
    "grok": "grok", "nordvpn": "nordvpn", "nord": "nordvpn",
    "youtube": "youtube", "yt": "youtube", "linkedin": "linkedin",
    "replit": "replit", "elevenlabs": "elevenlabs", "office": "office365",
}


def _ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def extract_product_signature(name: str, description: str = "") -> dict:
    text = _ascii(f"{name} {description[:700]}")
    compact = re.sub(r"[^a-z0-9]+", "", text)
    tokens = [token for token in re.findall(r"[a-z0-9]+", text) if token not in _STOP_WORDS]
    family = ""
    for token, canonical in _ALIASES.items():
        if token in compact:
            family = canonical
            break
    duration_months = None
    duration_days = None
    year = re.search(r"\b(\d{1,2})\s*(?:year|years|yr|yrs|y|an|ans|annee|annees)\b", text)
    month = re.search(r"\b(\d{1,3})\s*(?:month|months|mo|mos|m|mois)\b", text)
    day = re.search(r"\b(\d{1,4})\s*(?:day|days|d|jour|jours)\b", text)
    if year:
        duration_months = int(year.group(1)) * 12
    elif month:
        duration_months = int(month.group(1))
    elif day:
        duration_days = int(day.group(1))
    delivery_mode = "activation" if any(term in text for term in (
        "your account", "own account", "votre compte", "activation", "activate",
        "activer", "invite", "slot", "link", "lien"
    )) else "account" if any(term in text for term in (
        "email", "password", "mot de passe", "ready made", "compte fourni"
    )) else "unknown"
    access = "shared" if any(term in text for term in ("shared", "partage", "partagee")) and "no shared" not in text else "private" if any(
        term in text for term in ("private", "prive", "privee", "no shared", "own account")
    ) else "unknown"
    return {
        "family": family,
        "duration_months": duration_months,
        "duration_days": duration_days,
        "delivery_mode": delivery_mode,
        "access": access,
        "tokens": sorted(set(tokens))[:40],
    }


def compatibility_score(left: dict, right: dict) -> tuple[float, bool, str]:
    la = left.get("attributes") or extract_product_signature(left.get("name", ""), left.get("description", ""))
    ra = right.get("attributes") or extract_product_signature(right.get("name", ""), right.get("description", ""))
    if la["family"] and ra["family"] and la["family"] != ra["family"]:
        return 0.0, False, "different product family"
    for key in ("duration_months", "duration_days"):
        if la.get(key) and ra.get(key) and la[key] != ra[key]:
            return 0.0, False, f"different {key}"
    if la["delivery_mode"] != "unknown" and ra["delivery_mode"] != "unknown" and la["delivery_mode"] != ra["delivery_mode"]:
        return 0.0, False, "account and activation products are not interchangeable"
    if la["access"] != "unknown" and ra["access"] != "unknown" and la["access"] != ra["access"]:
        return 0.0, False, "private and shared products are not interchangeable"
    left_tokens, right_tokens = set(la["tokens"]), set(ra["tokens"])
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, _ascii(left.get("name", "")), _ascii(right.get("name", ""))).ratio()
    family_bonus = 0.25 if la["family"] and la["family"] == ra["family"] else 0.0
    score = min(0.99, family_bonus + jaccard * 0.45 + sequence * 0.30)
    return round(score, 4), score >= 0.46, "deterministic product attributes"


def rank_supplier_candidates(candidates: list[dict], unit_revenue: float) -> list[dict]:
    """Rank compatible offers without relying on AI at checkout time."""
    safe = []
    for candidate in candidates:
        cost = max(0.0, float(candidate.get("base_price") or 0))
        if cost <= 0 or cost >= max(0.0, float(unit_revenue or 0)):
            continue
        completed = max(0, int(candidate.get("completed_orders") or 0))
        failures = max(0, int(candidate.get("failed_orders") or 0))
        reliability = (completed + 3.0) / (completed + failures + 3.0)
        unknown_penalty = min(0.25, int(candidate.get("unknown_orders") or 0) * 0.03)
        score = cost + (1.0 - reliability + unknown_penalty) * max(0.05, cost * 0.15)
        safe.append({**candidate, "route_score": round(score, 6), "reliability": round(reliability, 4)})
    return sorted(safe, key=lambda row: (row["route_score"], float(row.get("base_price") or 0), str(row.get("supplier_code") or "")))


async def _gemini_review(pairs: list[dict]) -> dict[int, dict]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or not pairs:
        return {}
    model = os.environ.get("GEMINI_MATCH_MODEL", "gemini-2.5-flash").strip()
    safe_pairs = [{
        "id": pair["id"],
        "a": {"name": pair["anchor"]["name"], "description": pair["anchor"].get("description", "")[:500], "attributes": pair["anchor"]["attributes"]},
        "b": {"name": pair["candidate"]["name"], "description": pair["candidate"].get("description", "")[:500], "attributes": pair["candidate"]["attributes"]},
    } for pair in pairs]
    prompt = (
        "You review digital-product supplier offers. Decide whether A and B are exactly interchangeable for a customer. "
        "Different duration, account-vs-activation, private-vs-shared, region, seats, or required customer input means incompatible. "
        "Return JSON only: {\"decisions\":[{\"id\":1,\"compatible\":true,\"confidence\":0.97,\"reason\":\"...\"}]}. "
        "Never infer compatibility merely from the same brand. Data:\n" + json.dumps(safe_pairs, ensure_ascii=False)
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
            return {int(item["id"]): item for item in data.get("decisions", []) if isinstance(item, dict) and str(item.get("id", "")).isdigit()}
    except Exception:
        return {}


async def propose_supplier_routes(*, use_ai: bool = True, max_pairs: int = 80) -> dict:
    from database.suppliers import list_supplier_router_catalog, upsert_supplier_route_proposals

    catalog = await list_supplier_router_catalog()
    anchors = catalog["anchors"]
    products = catalog["products"]
    pairs = []
    pair_id = 0
    for anchor in anchors:
        ranked = []
        anchor = {**anchor, "attributes": extract_product_signature(anchor["name"], anchor.get("description", ""))}
        for candidate in products:
            if candidate["supplier_code"] == anchor["supplier_code"] or int(candidate["id"]) == int(anchor["id"]):
                continue
            if float(candidate.get("base_price") or 0) <= 0 or float(candidate.get("base_price") or 0) >= float(anchor.get("sale_price") or 0):
                continue
            if int(anchor.get("promised_warranty_days") or 0) > int(candidate.get("warranty_days") or 0):
                continue
            candidate = {**candidate, "attributes": extract_product_signature(candidate["name"], candidate.get("description", ""))}
            score, compatible, reason = compatibility_score(anchor, candidate)
            if compatible:
                ranked.append((score, candidate, reason))
        for score, candidate, reason in sorted(ranked, key=lambda item: item[0], reverse=True)[:5]:
            pair_id += 1
            pairs.append({"id": pair_id, "anchor": anchor, "candidate": candidate, "score": score, "reason": reason})
            if len(pairs) >= max(1, min(int(max_pairs), 200)):
                break
        if len(pairs) >= max(1, min(int(max_pairs), 200)):
            break
    ai = await _gemini_review(pairs) if use_ai else {}
    proposals = []
    for pair in pairs:
        decision = ai.get(pair["id"])
        if decision and not bool(decision.get("compatible")):
            continue
        confidence = float(decision.get("confidence", pair["score"])) if decision else pair["score"]
        if confidence < 0.55:
            continue
        proposals.append({
            "local_product_id": int(pair["anchor"]["local_product_id"]),
            "supplier_product_id": int(pair["candidate"]["id"]),
            "confidence": min(1.0, max(0.0, confidence)),
            "match_source": "gemini" if decision else "deterministic",
            "reason": str(decision.get("reason") if decision else pair["reason"])[:500],
            "attributes": pair["candidate"]["attributes"],
        })
    saved = await upsert_supplier_route_proposals(proposals)
    return {"anchors": len(anchors), "pairs_reviewed": len(pairs), "proposals": saved, "ai_used": bool(ai)}


__all__ = [
    "compatibility_score", "extract_product_signature", "propose_supplier_routes",
    "rank_supplier_candidates",
]
