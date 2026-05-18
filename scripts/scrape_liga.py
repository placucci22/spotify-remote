"""
Playwright scraper for ligapokemon.com.br — runs in GitHub Actions.
Stores results in Upstash Redis so the Vercel API can read them.
"""
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://www.ligapokemon.com.br"

# URL format confirmed from site: ?view=cards/search&card=categ%3D{N}+searchprod%3D1
# categ=10 → Caixas de Boosters (confirmed)
# categ=9  → Caixa Treinador Avançado (ETB) — to confirm
# categ=7  → Latas (tins) — to confirm
# categ=6  → Blisters — to confirm
# categ=11 → Box Colecionável — to confirm
CATEGORY_URLS = {
    "booster_box": f"{BASE_URL}/?view=cards/search&card=categ%3D10+searchprod%3D1",
    "etb":         f"{BASE_URL}/?view=cards/search&card=categ%3D9+searchprod%3D1",
    "tin":         f"{BASE_URL}/?view=cards/search&card=categ%3D7+searchprod%3D1",
    "blister":     f"{BASE_URL}/?view=cards/search&card=categ%3D6+searchprod%3D1",
    "collection":  f"{BASE_URL}/?view=cards/search&card=categ%3D11+searchprod%3D1",
}

KV_URL   = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ["KV_REST_API_URL"]
KV_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ["KV_REST_API_TOKEN"]
KV_KEY   = "liga_products_v1"
KV_TTL   = 90_000  # 25 hours

_debug_done = False  # print full HTML debug only once


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _parse_price(text: str) -> float | None:
    # Handle "R$ 650,00" → 650.0
    cleaned = re.sub(r"[^\d,.]", "", text or "")
    # Remove thousand separators: "1.650,00" → "1650.00"
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _extract_set_name(name: str) -> str:
    ignore = {
        "booster", "box", "display", "elite", "trainer", "etb", "tin",
        "blister", "coleção", "collection", "premium", "bundle", "pokemon",
        "pokémon", "tcg", "pack", "pacote", "caixa", "lata", "kit",
        "treinador", "avançado", "caixas", "boosters",
    }
    parts = name.split("-")
    if len(parts) > 1:
        return parts[-1].strip()
    words = name.split()
    filtered = [w for w in words if w.lower() not in ignore and len(w) > 2]
    return " ".join(filtered[:4]) if filtered else name


def _categorize_name(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["caixa de booster", "booster box", "display"]):
        return "booster_box"
    if any(k in n for k in ["treinador", "elite trainer", "etb"]):
        return "etb"
    if "lata" in n or "tin" in n:
        return "tin"
    if "blister" in n:
        return "blister"
    if any(k in n for k in ["colecionável", "collection", "bundle", "kit"]):
        return "collection"
    return "sealed"


def _debug_html(html: str, url: str):
    global _debug_done
    if _debug_done:
        return
    _debug_done = True
    soup = BeautifulSoup(html, "html.parser")
    print(f"\n[DEBUG] URL: {url}")
    print(f"[DEBUG] Page title: {soup.title.string if soup.title else 'NO TITLE'}")
    # Collect all unique class names
    all_classes = set()
    for el in soup.find_all(True):
        for cls in (el.get("class") or []):
            all_classes.add(cls)
    # Show classes that look product-related
    interesting = sorted(c for c in all_classes if any(
        k in c.lower() for k in ["prod", "card", "item", "price", "preco", "name", "nom"]
    ))
    print(f"[DEBUG] Interesting classes: {interesting[:40]}")
    # Print a snippet of the body HTML
    body = soup.find("body")
    body_text = str(body)[:4000] if body else html[:4000]
    print(f"[DEBUG] Body HTML (first 4000 chars):\n{body_text}\n[/DEBUG]\n")


def _parse_page(html: str, category: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Debug on first empty page to see real selectors
    if not soup.select("a"):
        _debug_html(html, page_url)

    products = []
    now = datetime.utcnow().isoformat()

    # Try multiple selector strategies — broaden on each attempt
    cards = (
        soup.select(".card-produto")
        or soup.select(".produto-item")
        or soup.select(".product-item")
        or soup.select("li.item")
        or soup.select("[class*='produto']")
        or soup.select("[class*='product']")
        or soup.select(".card:has(img):has(a)")
    )

    # Fallback: any element containing a price-looking text
    if not cards:
        # Collect all divs/articles that contain "R$"
        candidates = []
        for el in soup.find_all(["div", "article", "li"]):
            if "R$" in el.get_text():
                # Only take leaf-ish containers (not the whole page body)
                children_with_price = [c for c in el.find_all(["div", "article", "li"]) if "R$" in c.get_text()]
                if not children_with_price:
                    candidates.append(el)
        if candidates:
            print(f"  [parse] fallback: found {len(candidates)} R$-containing elements")
            _debug_html(html, page_url)
            cards = candidates[:50]

    if not cards:
        _debug_html(html, page_url)

    for card in cards:
        try:
            name_el = (
                card.select_one(".nome-produto")
                or card.select_one(".product-name")
                or card.select_one(".titulo")
                or card.select_one("[class*='nome']")
                or card.select_one("[class*='title']")
                or card.select_one("h2")
                or card.select_one("h3")
                or card.select_one("h4")
                or card.select_one("a[title]")
                or card.select_one("a")
            )
            # Price: skip "À partir de" text, look for the number
            price_el = (
                card.select_one(".preco-por")
                or card.select_one(".price-box .price")
                or card.select_one("[class*='preco']")
                or card.select_one("[class*='price']")
            )
            # If still no price el, search for text matching "R$"
            if not price_el:
                for el in card.find_all(True):
                    t = el.get_text(strip=True)
                    if re.search(r"R\$\s*[\d.,]+", t) and not el.find_all(True):
                        price_el = el
                        break

            link_el = card.select_one("a[href]")
            img_el  = card.select_one("img")

            if not name_el:
                continue

            name = name_el.get_text(strip=True) or name_el.get("title", "")
            if not name:
                continue

            price_text = price_el.get_text(strip=True) if price_el else ""
            price = _parse_price(price_text)
            if not price:
                continue

            href = (link_el.get("href", "") if link_el else "")
            url  = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
            img  = ""
            if img_el:
                img = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src") or ""

            stock_el = card.select_one(".estoque") or card.select_one("[class*='stock']") or card.select_one("[class*='estoque']")
            in_stock = True
            if stock_el:
                in_stock = "esgotado" not in stock_el.get_text(strip=True).lower()

            pid = hashlib.md5(f"{name}{url}".encode()).hexdigest()[:16]
            products.append({
                "id":         pid,
                "name":       name,
                "url":        url,
                "price_brl":  price,
                "category":   category,
                "set_name":   _extract_set_name(name),
                "image_url":  img,
                "in_stock":   in_stock,
                "seller":     "Liga Pokémon",
                "scraped_at": now,
            })
        except Exception as e:
            print(f"  [parse] error on card: {e}")

    return products


# ── Playwright scrape ────────────────────────────────────────────────────────

async def scrape() -> list[dict]:
    all_products: dict[str, dict] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        for category, base_url in CATEGORY_URLS.items():
            print(f"\n[{category}] {base_url}")
            for page_num in range(1, 11):
                # Pagination: append pagina=N to the card param
                if page_num == 1:
                    url = base_url
                else:
                    # Try: base_url + "+pagina%3D{N}"
                    url = base_url + f"+pagina%3D{page_num}"

                try:
                    resp = await page.goto(url, wait_until="networkidle", timeout=45_000)
                    await page.wait_for_timeout(2500)  # let JS finish rendering

                    html = await page.content()
                    items = _parse_page(html, category, url)

                    if not items:
                        print(f"  page {page_num}: 0 items — stopping category")
                        break

                    new = 0
                    for item in items:
                        if item["id"] not in all_products:
                            all_products[item["id"]] = item
                            new += 1

                    print(f"  page {page_num}: {len(items)} items ({new} new)")
                    await asyncio.sleep(1.0)

                except Exception as e:
                    print(f"  page {page_num}: error — {e}")
                    break

        await browser.close()

    return list(all_products.values())


# ── KV store ─────────────────────────────────────────────────────────────────

def save_to_kv(products: list[dict], scraped_at: str) -> bool:
    payload = json.dumps({"products": products, "scraped_at": scraped_at}, ensure_ascii=False)
    r = requests.post(
        f"{KV_URL}/pipeline",
        json=[["SET", KV_KEY, payload, "EX", str(KV_TTL)]],
        headers={"Authorization": f"Bearer {KV_TOKEN}", "Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"  KV error: {r.status_code} {r.text[:200]}")
    return r.status_code == 200


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("=== Liga Pokémon scraper ===")
    products = await scrape()
    print(f"\nTotal: {len(products)} produtos")

    if not products:
        print("ERROR: 0 produtos encontrados — nada salvo no KV")
        sys.exit(1)

    scraped_at = datetime.utcnow().isoformat()
    ok = save_to_kv(products, scraped_at)
    print(f"KV save: {'OK' if ok else 'FAILED'}")

    if not ok:
        sys.exit(1)

    print("Concluído.")


if __name__ == "__main__":
    asyncio.run(main())
