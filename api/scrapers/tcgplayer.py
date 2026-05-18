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
    "Scarlet & Violet 151 ETB": "pokemon-sv3pt5-scarlet-violet-151/elite-trainer-box",
    "Scarlet & Violet Booster Box": "pokemon-sv1-scarlet-violet/booster-box",
    "Paldea Evolved Booster Box": "pokemon-sv2-paldea-evolved/booster-box",
    "Obsidian Flames Booster Box": "pokemon-sv3-obsidian-flames/booster-box",
    "Paradox Rift Booster Box": "pokemon-sv4-paradox-rift/booster-box",
    "Paradox Rift ETB": "pokemon-sv4-paradox-rift/elite-trainer-box",
    "Temporal Forces Booster Box": "pokemon-sv5-temporal-forces/booster-box",
    "Temporal Forces ETB": "pokemon-sv5-temporal-forces/elite-trainer-box",
    "Twilight Masquerade Booster Box": "pokemon-sv6-twilight-masquerade/booster-box",
    "Stellar Crown Booster Box": "pokemon-sv7-stellar-crown/booster-box",
    "Stellar Crown ETB": "pokemon-sv7-stellar-crown/elite-trainer-box",
    "Surging Sparks Booster Box": "pokemon-sv8-surging-sparks/booster-box",
    "Surging Sparks ETB": "pokemon-sv8-surging-sparks/elite-trainer-box",
    "Prismatic Evolutions ETB": "pokemon-sv8pt5-prismatic-evolutions/elite-trainer-box",
    "Journey Together Booster Box": "pokemon-sv9-journey-together/booster-box",
    "Journey Together ETB": "pokemon-sv9-journey-together/elite-trainer-box",
}

# PT-BR Liga Pokémon name fragments → English equivalents used in SEALED_PRODUCT_MAP.
# Longer phrases first so they match before shorter substrings.
_PTBR_FRAGMENTS = [
    # Set names (numbered first to avoid partial matches with base name)
    ("escarlate e violeta 9", "journey together"),
    ("escarlate e violeta 8", "surging sparks"),
    ("escarlate e violeta 7", "stellar crown"),
    ("escarlate e violeta 6", "twilight masquerade"),
    ("escarlate e violeta 5", "temporal forces"),
    ("escarlate e violeta 4", "paradox rift"),
    ("escarlate e violeta 3", "obsidian flames"),
    ("escarlate e violeta 2", "paldea evolved"),
    ("escarlate e violeta 1", "scarlet & violet"),
    # Named PT-BR set titles
    ("amigos de jornada", "journey together"),
    ("rivais predestinados", "destined rivals"),
    ("faíscas surpreendentes", "surging sparks"),
    ("faiscas surpreendentes", "surging sparks"),
    ("evoluções prismáticas", "prismatic evolutions"),
    ("evolucoes prismaticas", "prismatic evolutions"),
    ("coroa estelar", "stellar crown"),
    ("mascarada do crepúsculo", "twilight masquerade"),
    ("mascarada do crepusculo", "twilight masquerade"),
    ("forças temporais", "temporal forces"),
    ("forcas temporais", "temporal forces"),
    ("fenda paradoxal", "paradox rift"),
    ("chamas obsidiana", "obsidian flames"),
    ("evoluções em paldea", "paldea evolved"),
    ("evolucoes em paldea", "paldea evolved"),
    ("escarlate e violeta", "scarlet & violet"),
    # Product types
    ("caixa de treinador de elite", "elite trainer box"),
    ("caixa do treinador de elite", "elite trainer box"),
    ("caixa de booster", "booster box"),
]


def _normalize_name(name: str) -> Optional[str]:
    """
    Convert a Liga Pokémon product name to a normalized English form for TCGPlayer lookup.
    Returns None for Japanese/Chinese products (not on TCGPlayer).
    """
    lang_match = re.match(r"^\s*\(([^)]+)\)\s*", name)
    if lang_match:
        lang = lang_match.group(1).upper()
        if any(x in lang for x in ("JAP", "JP", "CHN", "CN")):
            return None
        rest = name[lang_match.end():]
    else:
        rest = name

    normalized = rest.lower()
    for ptbr, en in _PTBR_FRAGMENTS:
        normalized = normalized.replace(ptbr, en)

    return normalized


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

        text = soup.get_text()
        prices = re.findall(r"\$\s*([\d,]+\.?\d{0,2})", text)
        if prices:
            floats = [float(p.replace(",", "")) for p in prices]
            valid = [p for p in floats if 20 < p < 500]
            if valid:
                return min(valid)
        return None
    except Exception as e:
        print(f"[tcgplayer] Error fetching {url}: {e}")
        return None


def get_set_singles_prices(set_slug: str) -> list:
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
    Try to find TCGPlayer price for a product, supporting Portuguese Liga Pokémon names.
    Returns None for JAP/CHN products or unrecognized sets.
    """
    normalized = _normalize_name(product_name)
    if normalized is None:
        return None  # JAP/CHN — skip

    # Also try the original name lowercased for English products
    candidates = [normalized]
    if normalized != product_name.lower():
        candidates.append(product_name.lower())

    for name_lower in candidates:
        # Direct / substring match
        for key, slug in SEALED_PRODUCT_MAP.items():
            key_lower = key.lower()
            if key_lower in name_lower or name_lower in key_lower:
                price = get_sealed_price(slug)
                if price:
                    return price
                time.sleep(0.3)

        # Partial word overlap (≥2 meaningful words)
        for key, slug in SEALED_PRODUCT_MAP.items():
            key_words = set(key.lower().split()) - {"the", "a", "an", "of", "&"}
            name_words = set(name_lower.split()) - {"the", "a", "an", "of", "&"}
            if len(key_words & name_words) >= 2:
                price = get_sealed_price(slug)
                if price:
                    return price
                time.sleep(0.3)

    return None
