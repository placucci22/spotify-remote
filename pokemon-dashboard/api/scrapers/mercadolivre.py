"""
Mercado Livre public REST API scraper for Pokemon TCG products in Brazil.
No authentication or API key required.
"""
import requests
from urllib.parse import quote as url_quote
from datetime import datetime
from typing import Optional
import re

ML_API = "https://api.mercadolibre.com/sites/MLB/search"

SEARCH_QUERIES = [
    "booster box pokemon tcg",
    "elite trainer box pokemon",
    "display pokemon tcg",
    "tin pokemon tcg",
    "blister pack pokemon",
    "prismatic evolutions pokemon",
    "surging sparks pokemon",
    "journey together pokemon",
    "temporal forces pokemon",
    "twilight masquerade pokemon",
    "scarlet violet 151 pokemon",
]

SEALED_KEYWORDS = [
    "booster box", "display", "etb", "elite trainer",
    "tin", "blister", "bundle", "collection box", "coleção",
    "premium", "pacote", "selado", "sealed"
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PokePriceBot/1.0)",
    "Accept": "application/json",
}


def _categorize(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["booster box", "display", "caixa de booster"]):
        return "booster_box"
    if any(k in n for k in ["elite trainer", "etb"]):
        return "etb"
    if "tin" in n:
        return "tin"
    if "blister" in n:
        return "blister"
    if any(k in n for k in ["coleção", "collection", "premium", "bundle"]):
        return "collection"
    return "sealed"


def _extract_set_name(name: str) -> str:
    ignore = {
        "booster", "box", "display", "elite", "trainer", "etb", "tin",
        "blister", "coleção", "collection", "premium", "bundle", "pokemon",
        "pokémon", "tcg", "pack", "pacote", "caixa", "cards", "cartas",
        "selado", "sealed", "novo", "original",
    }
    words = re.sub(r"[^\w\s]", " ", name).split()
    filtered = [w for w in words if w.lower() not in ignore and len(w) > 2]
    return " ".join(filtered[:5]) if filtered else name


def _is_sealed(name: str) -> bool:
    n = name.lower()
    return any(kw in n for kw in SEALED_KEYWORDS)


def fetch_ml_products(limit_per_query: int = 50) -> list[dict]:
    """Fetch Pokemon sealed products from Mercado Livre Brazil."""
    all_products = {}  # id → product (dedup)

    for query in SEARCH_QUERIES:
        url = f"{ML_API}?q={url_quote(query)}&limit={limit_per_query}&condition=new"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"[ml] {resp.status_code} for query '{query}'")
                continue

            data = resp.json()
            for item in data.get("results", []):
                item_id = item.get("id")
                title = item.get("title", "")
                price = item.get("price")

                if not item_id or not title or not price:
                    continue
                if not _is_sealed(title):
                    continue
                if item_id in all_products:
                    continue

                all_products[item_id] = {
                    "id": item_id,
                    "name": title,
                    "url": item.get("permalink", ""),
                    "price_brl": float(price),
                    "category": _categorize(title),
                    "set_name": _extract_set_name(title),
                    "image_url": item.get("thumbnail", "").replace("http://", "https://"),
                    "in_stock": (item.get("available_quantity") or 0) > 0,
                    "seller": item.get("seller", {}).get("nickname", "Mercado Livre"),
                    "scraped_at": datetime.now().isoformat(),
                }

        except Exception as e:
            print(f"[ml] Error on query '{query}': {e}")

    products = list(all_products.values())
    print(f"[ml] Fetched {len(products)} sealed products")
    return products
