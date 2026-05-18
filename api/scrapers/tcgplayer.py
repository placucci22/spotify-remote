"""
TCGPlayer price fetcher.
Uses TCGPlayer's public market price pages for sealed products and singles.
"""
import requests
import re
import time
from typing import Optional
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SEALED_PRODUCT_MAP = {
    "Scarlet & Violet 151 Booster Box": "pokemon-sv3pt5-scarlet-violet-151/booster-box",
    "Scarlet & Violet Booster Box": "pokemon-sv1-scarlet-violet/booster-box",
    "Paldea Evolved Booster Box": "pokemon-sv2-paldea-evolved/booster-box",
    "Obsidian Flames Booster Box": "pokemon-sv3-obsidian-flames/booster-box",
    "Paradox Rift Booster Box": "pokemon-sv4-paradox-rift/booster-box",
    "Temporal Forces Booster Box": "pokemon-sv5-temporal-forces/booster-box",
    "Twilight Masquerade Booster Box": "pokemon-sv6-twilight-masquerade/booster-box",
    "Stellar Crown Booster Box": "pokemon-sv7-stellar-crown/booster-box",
    "Surging Sparks Booster Box": "pokemon-sv8-surging-sparks/booster-box",
    "Prismatic Evolutions ETB": "pokemon-sv8pt5-prismatic-evolutions/elite-trainer-box",
    "Journey Together Booster Box": "pokemon-sv9-journey-together/booster-box",
    "Scarlet & Violet 151 ETB": "pokemon-sv3pt5-scarlet-violet-151/elite-trainer-box",
    "Paradox Rift ETB": "pokemon-sv4-paradox-rift/elite-trainer-box",
    "Temporal Forces ETB": "pokemon-sv5-temporal-forces/elite-trainer-box",
    "Stellar Crown ETB": "pokemon-sv7-stellar-crown/elite-trainer-box",
}

BASE_URL = "https://www.tcgplayer.com/product"


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def get_sealed_price(product_slug: str) -> Optional[float]:
    """
    Fetch market price for a sealed product from TCGPlayer.
    product_slug: e.g. 'pokemon-sv3pt5-scarlet-violet-151/booster-box'
    """
    url = f"{BASE_URL}/{product_slug}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        price_el = (
            soup.select_one(".spotlight__price")
            or soup.select_one("[class*='market-price']")
            or soup.select_one(".price-point__data")
            or soup.select_one("[data-testid='listed-price']")
        )
        if price_el:
            return _parse_price(price_el.get_text(strip=True))

        # Fallback: search for $ pattern in page
        text = soup.get_text()
        prices = re.findall(r"\$\s*([\d,]+\.?\d{0,2})", text)
        if prices:
            floats = [float(p.replace(",", "")) for p in prices]
            # Filter to reasonable sealed product range ($20–$500)
            valid = [p for p in floats if 20 < p < 500]
            if valid:
                return min(valid)
        return None
    except Exception as e:
        print(f"[tcgplayer] Error fetching {url}: {e}")
        return None


def get_set_singles_prices(set_slug: str) -> list[dict]:
    """
    Fetch all single card prices for a set from TCGPlayer.
    Returns a list of {name, rarity, market_price_usd}.
    """
    url = f"https://www.tcgplayer.com/search/pokemon/{set_slug}?productLineName=pokemon&setName={set_slug}&view=grid&page=1&pageSize=100"
    cards = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        card_items = soup.select(".search-result") or soup.select("[class*='product-card']")

        for item in card_items:
            name_el = item.select_one(".product-card__title") or item.select_one("[class*='title']")
            price_el = item.select_one(".product-card__market-price") or item.select_one("[class*='price']")
            rarity_el = item.select_one(".product-card__rarity") or item.select_one("[class*='rarity']")

            if name_el and price_el:
                price = _parse_price(price_el.get_text(strip=True))
                if price is not None:
                    cards.append({
                        "name": name_el.get_text(strip=True),
                        "rarity": rarity_el.get_text(strip=True) if rarity_el else "Unknown",
                        "market_price_usd": price,
                    })
        time.sleep(0.5)
    except Exception as e:
        print(f"[tcgplayer] Error fetching singles for {set_slug}: {e}")
    return cards


def get_price_for_product_name(product_name: str) -> Optional[float]:
    """
    Try to find TCGPlayer price using the known product map,
    or search if not found.
    """
    # Direct match
    name_lower = product_name.lower()
    for key, slug in SEALED_PRODUCT_MAP.items():
        if key.lower() in name_lower or name_lower in key.lower():
            price = get_sealed_price(slug)
            if price:
                return price
            time.sleep(0.5)

    # Partial match
    for key, slug in SEALED_PRODUCT_MAP.items():
        key_words = set(key.lower().split())
        name_words = set(name_lower.split())
        overlap = key_words & name_words
        if len(overlap) >= 3:
            price = get_sealed_price(slug)
            if price:
                return price
            time.sleep(0.5)

    return None
