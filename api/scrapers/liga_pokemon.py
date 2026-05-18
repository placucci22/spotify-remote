"""
Scraper for ligapokemon.com.br
Fetches sealed product listings (booster boxes, ETBs, tins, etc.)
"""
import cloudscraper
from urllib.parse import quote as url_quote
from bs4 import BeautifulSoup
import hashlib
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# cloudscraper handles Cloudflare / anti-bot challenges automatically
_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

BASE_URL = "https://www.ligapokemon.com.br"

CATEGORY_URLS = {
    "booster_box": f"{BASE_URL}/?view=cards/list&CategoriasId=2",
    "etb": f"{BASE_URL}/?view=cards/list&CategoriasId=3",
    "tin": f"{BASE_URL}/?view=cards/list&CategoriasId=4",
    "blister": f"{BASE_URL}/?view=cards/list&CategoriasId=5",
    "collection": f"{BASE_URL}/?view=cards/list&CategoriasId=6",
}

SEALED_KEYWORDS = [
    "booster box", "display", "etb", "elite trainer",
    "tin", "blister", "coleção", "colecao", "bundle",
    "premium", "collection box", "caixa", "pacote"
]


def _make_product_id(name: str, url: str) -> str:
    return hashlib.md5(f"{name}{url}".encode()).hexdigest()[:16]


def _parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_sealed_product(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in SEALED_KEYWORDS)


def _categorize(name: str) -> str:
    name_lower = name.lower()
    if any(k in name_lower for k in ["booster box", "display", "caixa de booster"]):
        return "booster_box"
    if any(k in name_lower for k in ["elite trainer", "etb"]):
        return "etb"
    if "tin" in name_lower:
        return "tin"
    if "blister" in name_lower:
        return "blister"
    if any(k in name_lower for k in ["coleção", "collection", "premium", "bundle"]):
        return "collection"
    return "sealed"


def _extract_set_name(name: str) -> str:
    """Try to extract the Pokemon set name from a product title."""
    ignore = [
        "booster box", "display", "elite trainer box", "etb", "tin",
        "blister", "coleção", "collection", "premium", "bundle",
        "pokemon", "pokémon", "tcg", "box", "pack", "pacote", "caixa"
    ]
    parts = name.split("-")
    if len(parts) > 1:
        return parts[-1].strip()
    words = name.split()
    filtered = [w for w in words if w.lower() not in ignore and len(w) > 2]
    return " ".join(filtered[:4]) if filtered else name


def scrape_products(max_pages: int = 3) -> list[dict]:
    """Quick sequential scrape — used for on-demand refresh (2-3 pages per category)."""
    products = []
    seen_ids = set()

    for category, base_url in CATEGORY_URLS.items():
        for page in range(1, max_pages + 1):
            url = f"{base_url}&pagina={page}"
            try:
                resp = _scraper.get(url, timeout=10)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                items = _parse_product_list(soup, category)
                if not items:
                    break
                for item in items:
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        products.append(item)
                time.sleep(0.3)
            except Exception as e:
                print(f"[liga_pokemon] Error scraping {url}: {e}")
                break

    if not products:
        products = _scrape_search_fallback()

    return products


def scrape_all_categories(max_pages: int = 6, max_workers: int = 8, request_timeout: int = 8) -> list[dict]:
    """
    Full parallel scrape of all categories — used by the daily cron job.
    Fetches all category × page combinations concurrently.
    """
    tasks = [
        (category, page, f"{base_url}&pagina={page}")
        for category, base_url in CATEGORY_URLS.items()
        for page in range(1, max_pages + 1)
    ]

    def fetch_page(task):
        category, page, url = task
        try:
            resp = _scraper.get(url, timeout=request_timeout)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            return _parse_product_list(soup, category)
        except Exception as e:
            print(f"[liga_pokemon] Error {url}: {e}")
            return []

    products = []
    seen_ids = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_page, task): task for task in tasks}
        for future in as_completed(futures, timeout=25):
            try:
                for item in future.result():
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        products.append(item)
            except Exception:
                pass

    print(f"[liga_pokemon] Full scrape complete: {len(products)} products")
    return products


def _parse_product_list(soup: BeautifulSoup, category: str) -> list[dict]:
    products = []

    # Liga Pokémon product card selectors (adapt if site changes)
    product_cards = (
        soup.select(".card-produto")
        or soup.select(".produto-item")
        or soup.select("[class*='product']")
        or soup.select(".item")
    )

    for card in product_cards:
        try:
            name_el = (
                card.select_one(".nome-produto")
                or card.select_one(".product-name")
                or card.select_one("h2")
                or card.select_one("h3")
                or card.select_one("a[title]")
            )
            price_el = (
                card.select_one(".preco")
                or card.select_one(".price")
                or card.select_one("[class*='preco']")
                or card.select_one("[class*='price']")
            )
            link_el = card.select_one("a[href]")
            img_el = card.select_one("img")

            if not name_el or not price_el:
                continue

            name = name_el.get_text(strip=True) or name_el.get("title", "")
            if not name:
                continue

            price = _parse_price(price_el.get_text(strip=True))
            if not price:
                continue

            href = link_el.get("href", "") if link_el else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            image_url = img_el.get("src", "") if img_el else None

            stock_el = card.select_one(".estoque") or card.select_one("[class*='stock']")
            in_stock = True
            if stock_el:
                in_stock = "esgotado" not in stock_el.get_text(strip=True).lower()

            pid = _make_product_id(name, url)
            products.append({
                "id": pid,
                "name": name,
                "url": url,
                "price_brl": price,
                "category": category,
                "set_name": _extract_set_name(name),
                "image_url": image_url,
                "in_stock": in_stock,
                "seller": "Liga Pokémon",
                "scraped_at": datetime.now().isoformat(),
            })
        except Exception as e:
            print(f"[liga_pokemon] Error parsing card: {e}")
            continue

    return products


def _scrape_search_fallback() -> list[dict]:
    """Fallback: search for sealed products using the search endpoint."""
    products = []
    search_terms = ["booster box", "elite trainer box", "tin pokemon"]

    for term in search_terms:
        url = f"{BASE_URL}/?view=cards/list&q={url_quote(term)}"
        try:
            resp = _scraper.get(url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = _parse_product_list(soup, "sealed")
                products.extend(items)
            time.sleep(1.5)
        except Exception as e:
            print(f"[liga_pokemon] Search fallback error for '{term}': {e}")

    return products


def scrape_product_detail(url: str) -> Optional[dict]:
    """Fetch extra details from a product page."""
    try:
        resp = _scraper.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_el = soup.select_one(".descricao") or soup.select_one(".description")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        return {"description": desc}
    except Exception:
        return None
