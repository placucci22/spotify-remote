"""
PokemonPriceTracker.com API service.
Docs: https://www.pokemonpricetracker.com/api-reference

Free tier: 100 credits/day (1 credit per card/product queried).
We cache all results in KV (23h TTL) to stay well within limits.

Set POKEPRICE_API_KEY env var in Vercel / local .env.
"""
from __future__ import annotations

import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
import requests

_API_KEY = os.getenv("POKEPRICE_API_KEY", "")
_BASE = "https://www.pokemonpricetracker.com/api/v2"

# ── In-memory cache (per container lifetime) ─────────────────────────────────
_mem: dict[str, tuple[datetime, object]] = {}
_MEM_TTL = timedelta(hours=23)


def _mem_get(key: str):
    if key in _mem:
        ts, val = _mem[key]
        if datetime.now() - ts < _MEM_TTL:
            return val
    return None


def _mem_set(key: str, val) -> None:
    _mem[key] = (datetime.now(), val)


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(endpoint: str, params: dict) -> Optional[dict]:
    if not _API_KEY:
        print("[pokeprice] POKEPRICE_API_KEY not set")
        return None
    try:
        r = requests.get(
            f"{_BASE}/{endpoint.lstrip('/')}",
            headers={"Authorization": f"Bearer {_API_KEY}"},
            params=params,
            timeout=10,
        )
        remaining = r.headers.get("X-RateLimit-Daily-Remaining", "?")
        print(f"[pokeprice] {endpoint} status={r.status_code} credits_left={remaining}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            print("[pokeprice] Invalid API key")
        elif r.status_code == 429:
            print("[pokeprice] Daily credit limit reached")
        return None
    except Exception as e:
        print(f"[pokeprice] request error: {e}")
        return None


def _post(endpoint: str, body: dict) -> Optional[dict]:
    if not _API_KEY:
        return None
    try:
        r = requests.post(
            f"{_BASE}/{endpoint.lstrip('/')}",
            headers={"Authorization": f"Bearer {_API_KEY}", "Content-Type": "application/json"},
            json=body,
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[pokeprice] post error: {e}")
        return None


# ── Name normalisation helpers ────────────────────────────────────────────────

_PTBR_TO_EN = [
    ("amigos de jornada", "journey together"),
    ("faíscas surpreendentes", "surging sparks"),
    ("evoluções prismáticas", "prismatic evolutions"),
    ("mascarada do crepúsculo", "twilight masquerade"),
    ("forças temporais", "temporal forces"),
    ("coroa estelar", "stellar crown"),
    ("fenda paradoxal", "paradox rift"),
    ("chamas obsidiana", "obsidian flames"),
    ("evoluções em paldea", "paldea evolved"),
    ("escarlate e violeta 151", "scarlet & violet 151"),
    ("escarlate e violeta 9", "journey together"),
    ("escarlate e violeta 8", "surging sparks"),
    ("escarlate e violeta 7.5", "prismatic evolutions"),
    ("escarlate e violeta 7", "stellar crown"),
    ("escarlate e violeta 6.5", "twilight masquerade"),
    ("escarlate e violeta 6", "temporal forces"),
    ("escarlate e violeta 5", "temporal forces"),
    ("escarlate e violeta 4", "paradox rift"),
    ("escarlate e violeta 3.5", "scarlet & violet 151"),
    ("escarlate e violeta 3", "obsidian flames"),
    ("escarlate e violeta 2", "paldea evolved"),
    # Sealed product types
    ("caixa de booster", "booster box"),
    ("caixa de treinador de elite", "elite trainer box"),
    ("coleção treinador avançado", "elite trainer box"),
    ("blister", "blister pack"),
]

_LANG_RE = re.compile(r"^\s*\(([^)]+)\)\s*")


def normalize_product_name(name: str) -> tuple[str, str]:
    """Return (normalized_english_name, language_code)."""
    name = name.strip()
    lang = "en"
    m = _LANG_RE.match(name)
    if m:
        code = m.group(1).upper()
        if any(x in code for x in ("JAP", "JP")):
            lang = "jp"
        elif any(x in code for x in ("PT", "BR", "POR")):
            lang = "pt"
        elif any(x in code for x in ("ING", "EN")):
            lang = "en"
        name = name[m.end():]
    lower = name.lower()
    for ptbr, en in _PTBR_TO_EN:
        lower = lower.replace(ptbr, en)
    return lower.strip(" -–·"), lang


# ── Public API ────────────────────────────────────────────────────────────────

def get_sealed_price(product_name: str) -> Optional[float]:
    """
    Return the TCGPlayer market price (USD) for a sealed product.
    Normalises PT-BR names. Skips JP/CN products (not on TCGPlayer EN).
    Uses in-memory cache to avoid repeated credit usage.
    """
    normalized, lang = normalize_product_name(product_name)
    if lang in ("jp", "cn"):
        return None

    cache_key = f"sealed:{normalized}"
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached

    data = _get("sealed-products", {"search": normalized, "language": "english", "limit": 3})
    if not data:
        return None

    products = data if isinstance(data, list) else data.get("products", data.get("data", []))
    if not products:
        _mem_set(cache_key, None)
        return None

    # Pick the first result's market price
    price = _extract_price(products[0])
    _mem_set(cache_key, price)
    return price


def get_card_price(card_name: str, set_name: str = "", language: str = "english") -> Optional[float]:
    """Return market price (USD) for a single card."""
    cache_key = f"card:{card_name.lower()}:{set_name.lower()}"
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached

    params: dict = {"search": card_name, "language": language, "limit": 3}
    if set_name:
        params["set"] = set_name
    data = _get("cards", params)
    if not data:
        return None

    cards = data if isinstance(data, list) else data.get("cards", data.get("data", []))
    price = _extract_price(cards[0]) if cards else None
    _mem_set(cache_key, price)
    return price


def get_top_cards_for_set(set_name: str, limit: int = 10, language: str = "english") -> list[dict]:
    """
    Return the `limit` most expensive cards in a set.
    Used to populate/refresh STATIC_EV_DATA top_hits dynamically.
    Costs `limit` credits — use sparingly and cache results.
    """
    cache_key = f"set_top:{set_name.lower()}:{limit}"
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached

    data = _get("cards", {
        "set": set_name,
        "language": language,
        "sortBy": "price",
        "sortOrder": "desc",
        "limit": limit,
    })
    if not data:
        return []

    raw = data if isinstance(data, list) else data.get("cards", data.get("data", []))
    result = []
    for c in raw:
        price = _extract_price(c)
        if price:
            result.append({
                "name": c.get("name", ""),
                "rarity": c.get("rarity", "Unknown"),
                "price_usd": price,
                "set": c.get("set", set_name),
                "number": c.get("number", ""),
            })
    _mem_set(cache_key, result)
    return result


def parse_product_title(title: str) -> Optional[dict]:
    """
    Use the parse-title endpoint to match a Liga product name to a known card/product.
    Returns matched card data or None.
    """
    cache_key = f"parse:{title.lower()[:60]}"
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached

    result = _post("parse-title", {
        "title": title,
        "options": {"fuzzyMatching": True, "maxSuggestions": 1, "includeConfidence": True},
    })
    _mem_set(cache_key, result)
    return result


def get_sets(language: str = "english") -> list[dict]:
    """Return list of all sets (cached, zero extra cost if already fetched)."""
    cache_key = f"sets:{language}"
    cached = _mem_get(cache_key)
    if cached is not None:
        return cached

    data = _get("sets", {"language": language, "sortBy": "releaseDate", "sortOrder": "desc"})
    if not data:
        return []
    sets = data if isinstance(data, list) else data.get("sets", data.get("data", []))
    _mem_set(cache_key, sets)
    return sets


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_price(item: dict) -> Optional[float]:
    """Pull market price out of a pokeprice API response item."""
    if not item:
        return None
    # Try common price field structures
    prices = item.get("prices") or item.get("price") or {}
    if isinstance(prices, (int, float)):
        return float(prices)
    if isinstance(prices, dict):
        # Try in order: market → mid → low
        for key in ("market", "marketPrice", "mid", "low", "retail"):
            v = prices.get(key)
            if v:
                return float(v)
        # Nested by condition: {"normal": {"market": ...}, "holofoil": {"market": ...}}
        for condition_prices in prices.values():
            if isinstance(condition_prices, dict):
                v = condition_prices.get("market") or condition_prices.get("marketPrice")
                if v:
                    return float(v)
    return None
