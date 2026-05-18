"""
Playwright scraper for ligapokemon.com.br — runs locally on Mac (home IP bypasses Cloudflare).
Stores results in Upstash Redis so the Vercel API can read them.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote as url_quote

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Load .env file if present (for local runs)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

BASE_URL = "https://www.ligapokemon.com.br"

CATEGORY_URLS = {
    "booster_box":    f"{BASE_URL}/?view=cards/search&card=categ%3D10+searchprod%3D1",
    "etb":            f"{BASE_URL}/?view=cards%2Fsearch&card=categ%3D27+searchprod%3D1&tipo=1",
    "tin":            f"{BASE_URL}/?view=cards%2Fsearch&card=categ%3D24+searchprod%3D1&tipo=1",
    "blister":        f"{BASE_URL}/?view=cards%2Fsearch&card=categ%3D25+searchprod%3D1&tipo=1",
    "booster_single": f"{BASE_URL}/?view=cards/search&card=categ%3D21+searchprod%3D1",
}

KV_URL   = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN", "")
KV_KEY   = "liga_products_v1"
KV_TTL   = 90_000  # 25 hours


# ── Helpers ──────────────────────────────────────────────────────────────────

def _page_url(base: str, page_num: int) -> str:
    if page_num == 1:
        return base
    # Pagination must go at the end of the card= value, before any trailing &param
    # e.g. &card=categ%3D10+searchprod%3D1  →  ...+pagina%3DN
    # e.g. &card=categ%3D27+searchprod%3D1&tipo=1  →  ...+pagina%3DN&tipo=1
    card_idx = base.find("card=")
    if card_idx == -1:
        return base + f"+pagina%3D{page_num}"
    next_amp = base.find("&", card_idx)
    if next_amp == -1:
        return base + f"+pagina%3D{page_num}"
    return base[:next_amp] + f"+pagina%3D{page_num}" + base[next_amp:]


def _is_challenge(html: str) -> bool:
    return (
        "cf-turnstile" in html
        or "verificação de segurança" in html.lower()
        or "just a moment" in html.lower()
        or "enable javascript" in html.lower()
    )


def _parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "").replace(",", ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _categorize(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["booster box", "display", "caixa de booster"]):
        return "booster_box"
    if any(k in n for k in ["elite trainer", "etb", "caixa de treinador"]):
        return "etb"
    if "tin" in n or "lata" in n:
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
        "pokémon", "tcg", "pack", "pacote", "caixa", "lata", "avulso",
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

    # .card elements that don't contain nested .card (skip best-sellers containers)
    all_cards = soup.select(".card")
    cards = [c for c in all_cards if not c.select(".card")]

    for card in cards:
        try:
            name_el  = card.select_one("h5.card-title a") or card.select_one("h5.card-title")
            price_el = card.select_one(".smallest-price")
            link_el  = card.select_one("h5.card-title a") or card.select_one("a[href]")
            img_el   = card.select_one("img")

            if not name_el or not price_el:
                continue

            name  = name_el.get_text(strip=True)
            price = _parse_price(price_el.get_text(strip=True))

            if not name or not price:
                continue

            href = link_el.get("href", "") if link_el else ""
            url  = href if href.startswith("http") else f"{BASE_URL}{href}"
            img  = (img_el.get("src") or img_el.get("data-src") or "") if img_el else ""
            if img.startswith("//"):
                img = "https:" + img

            in_stock = "esgotado" not in card.get_text(strip=True).lower()

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
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        for category, base_url in CATEGORY_URLS.items():
            print(f"\n[{category}]")
            for page_num in range(1, 21):
                url = _page_url(base_url, page_num)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    # Wait for product cards to appear
                    try:
                        await page.wait_for_selector(".card h5.card-title", timeout=8_000)
                    except Exception:
                        await page.wait_for_timeout(5_000)
                    html = await page.content()

                    if _is_challenge(html):
                        print(f"  page {page_num}: Cloudflare challenge detected — cannot proceed")
                        break

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
                    await asyncio.sleep(1.0)

                except Exception as e:
                    print(f"  page {page_num}: error — {e}")
                    break

        await browser.close()

    return list(all_products.values())


# ── KV store ─────────────────────────────────────────────────────────────────

def save_to_kv(products: list[dict], scraped_at: str) -> bool:
    if not KV_URL or not KV_TOKEN:
        print("ERROR: KV_REST_API_URL / KV_REST_API_TOKEN not set")
        return False
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
