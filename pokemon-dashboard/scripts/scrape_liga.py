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
from urllib.parse import quote as url_quote

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://www.ligapokemon.com.br"

CATEGORY_URLS = {
    "booster_box": f"{BASE_URL}/?view=cards/list&CategoriasId=2",
    "etb":         f"{BASE_URL}/?view=cards/list&CategoriasId=3",
    "tin":         f"{BASE_URL}/?view=cards/list&CategoriasId=4",
    "blister":     f"{BASE_URL}/?view=cards/list&CategoriasId=5",
    "collection":  f"{BASE_URL}/?view=cards/list&CategoriasId=6",
}

KV_URL   = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ["KV_REST_API_URL"]
KV_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ["KV_REST_API_TOKEN"]
KV_KEY   = "liga_products_v1"
KV_TTL   = 90_000  # 25 hours


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "").replace(",", ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _categorize(name: str) -> str:
    n = name.lower()
    # Non-booster accessories — must check before generic "caixa" matches
    if any(k in n for k in ["caixa vazia", "pasta", "sleeve", "protetor", "dado", "play mat", "tapete", "deck box"]):
        return "accessory"
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
        "pokémon", "tcg", "box", "pack", "pacote", "caixa",
    }
    parts = name.split("-")
    if len(parts) > 1:
        return parts[-1].strip()
    words = name.split()
    filtered = [w for w in words if w.lower() not in ignore and len(w) > 2]
    return " ".join(filtered[:4]) if filtered else name


def _parse_page(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products = []
    now = datetime.utcnow().isoformat()

    cards = (
        soup.select(".card-produto")
        or soup.select(".produto-item")
        or soup.select("[class*='product-item']")
        or soup.select("[class*='produto']")
        or soup.select(".item")
    )

    for card in cards:
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
            link_el  = card.select_one("a[href]")
            img_el   = card.select_one("img")

            if not name_el or not price_el:
                continue

            name  = name_el.get_text(strip=True) or name_el.get("title", "")
            price = _parse_price(price_el.get_text(strip=True))

            if not name or not price:
                continue

            href = (link_el.get("href", "") if link_el else "")
            url  = href if href.startswith("http") else f"{BASE_URL}{href}"
            img  = (img_el.get("src") or img_el.get("data-src") or "") if img_el else ""

            stock_el = card.select_one(".estoque") or card.select_one("[class*='stock']")
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
        )
        page = await context.new_page()

        for category, base_url in CATEGORY_URLS.items():
            print(f"\n[{category}]")
            for page_num in range(1, 11):
                url = f"{base_url}&pagina={page_num}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await page.wait_for_timeout(1500)  # let JS render
                    html = await page.content()
                    items = _parse_page(html, category)

                    if not items:
                        print(f"  page {page_num}: 0 items — stopping category")
                        break

                    new = 0
                    for item in items:
                        if item["id"] not in all_products:
                            all_products[item["id"]] = item
                            new += 1

                    print(f"  page {page_num}: {len(items)} items ({new} new)")
                    await asyncio.sleep(0.8)

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
