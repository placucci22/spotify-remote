"""
PriceCharting.com scraper for sealed Pokemon product prices and trends.
PriceCharting tracks historical sealed product prices.
"""
import requests
import re
import time
from typing import Optional
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.pricecharting.com"

# Map of product name fragments to PriceCharting URLs
PRODUCT_SLUG_MAP = {
    "scarlet violet 151": "pokemon-scarlet-violet-151/booster-box",
    "scarlet & violet 151": "pokemon-scarlet-violet-151/booster-box",
    "pokemon 151": "pokemon-scarlet-violet-151/booster-box",
    "paldea evolved": "pokemon-paldea-evolved/booster-box",
    "obsidian flames": "pokemon-obsidian-flames/booster-box",
    "paradox rift": "pokemon-paradox-rift/booster-box",
    "temporal forces": "pokemon-temporal-forces/booster-box",
    "twilight masquerade": "pokemon-twilight-masquerade/booster-box",
    "stellar crown": "pokemon-stellar-crown/booster-box",
    "surging sparks": "pokemon-surging-sparks/booster-box",
    "prismatic evolutions": "pokemon-prismatic-evolutions/booster-box",
    "journey together": "pokemon-journey-together/booster-box",
    "scarlet violet base": "pokemon-scarlet-violet/booster-box",
    "base scarlet violet": "pokemon-scarlet-violet/booster-box",
}

ETB_SLUG_MAP = {
    "scarlet violet 151 etb": "pokemon-scarlet-violet-151/elite-trainer-box",
    "prismatic evolutions etb": "pokemon-prismatic-evolutions/elite-trainer-box",
    "paradox rift etb": "pokemon-paradox-rift/elite-trainer-box",
    "temporal forces etb": "pokemon-temporal-forces/elite-trainer-box",
}


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def get_sealed_price_and_trend(product_name: str) -> dict:
    """
    Fetch sealed product price and 30-day trend from PriceCharting.
    Returns: {sealed_usd, used_usd, thirty_day_change_pct, trend}
    """
    slug = _find_slug(product_name)
    if not slug:
        return {"sealed_usd": None, "used_usd": None, "thirty_day_change_pct": None, "trend": "UNKNOWN"}

    url = f"{BASE_URL}/game/{slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return {"sealed_usd": None, "used_usd": None, "thirty_day_change_pct": None, "trend": "UNKNOWN"}

        soup = BeautifulSoup(resp.text, "html.parser")
        return _parse_price_page(soup)
    except Exception as e:
        print(f"[pricecharting] Error fetching {url}: {e}")
        return {"sealed_usd": None, "used_usd": None, "thirty_day_change_pct": None, "trend": "UNKNOWN"}


def _find_slug(product_name: str) -> Optional[str]:
    name_lower = product_name.lower()

    # Check ETB map first
    for key, slug in ETB_SLUG_MAP.items():
        if key in name_lower:
            return slug

    # Then booster box map
    for key, slug in PRODUCT_SLUG_MAP.items():
        if key in name_lower:
            return slug

    # Try PriceCharting search
    return _search_pricecharting(product_name)


def _search_pricecharting(query: str) -> Optional[str]:
    url = f"{BASE_URL}/search-products?q={requests.utils.quote(query)}&type=prices"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        result = soup.select_one(".search-result a") or soup.select_one("table.games a")
        if result:
            href = result.get("href", "")
            # Extract slug from URL like /game/pokemon-xxx/booster-box
            match = re.search(r"/game/(.+)", href)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _parse_price_page(soup: BeautifulSoup) -> dict:
    result = {"sealed_usd": None, "used_usd": None, "thirty_day_change_pct": None, "trend": "STABLE"}

    # PriceCharting price table structure
    rows = soup.select("table#price-data tr") or soup.select(".price-table tr")
    for row in rows:
        cells = row.select("td")
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            val = cells[1].get_text(strip=True)
            price = _parse_price(val)
            if "sealed" in label or "new" in label:
                result["sealed_usd"] = price
            elif "used" in label or "complete" in label:
                result["used_usd"] = price

    # Try to get price from the main price display
    if not result["sealed_usd"]:
        price_els = (
            soup.select("[id*='sealed'] .price")
            or soup.select(".price-box .price")
            or soup.select("#used_price")
        )
        for el in price_els:
            price = _parse_price(el.get_text(strip=True))
            if price:
                result["sealed_usd"] = price
                break

    # Try to determine trend from chart data or price change indicators
    change_el = soup.select_one(".price-change") or soup.select_one("[class*='change']")
    if change_el:
        change_text = change_el.get_text(strip=True)
        change_match = re.search(r"([+-]?\d+\.?\d*)%", change_text)
        if change_match:
            change_pct = float(change_match.group(1))
            result["thirty_day_change_pct"] = change_pct
            if change_pct > 5:
                result["trend"] = "INCREASING"
            elif change_pct < -5:
                result["trend"] = "DECREASING"
            else:
                result["trend"] = "STABLE"

    return result


def get_historical_prices(product_slug: str, days: int = 90) -> list[dict]:
    """Fetch historical price data points for trend analysis."""
    url = f"{BASE_URL}/game/{product_slug}/price-history"
    data_points = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        # Parse chart data embedded in page JS
        text = resp.text
        match = re.search(r"chartData\s*=\s*(\[.+?\]);", text, re.DOTALL)
        if match:
            import json
            raw = json.loads(match.group(1))
            for point in raw[-days:]:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    data_points.append({"date": point[0], "price_usd": point[1]})
    except Exception as e:
        print(f"[pricecharting] Historical price error: {e}")
    return data_points
