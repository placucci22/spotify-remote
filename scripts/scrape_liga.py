"""
Playwright scraper for ligapokemon.com.br.
Runs locally (Mac/Linux) or on Render.com cron.
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

KV_URL   = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ["KV_REST_API_URL"]
KV_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ["KV_REST_API_TOKEN"]
KV_KEY   = "liga_products_v1"
KV_TTL   = 90_000  # 25 hours

_debug_done = False


def _page_url(base: str, page_num: int) -> str:
    if page_num == 1:
        return base
    if "&" in base:
        idx = base.index("&")
        return base[:idx] + f"+pagina%3D{page_num}" + base[idx:]
    return base + f"+pagina%3D{page_num}"


def _parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "")
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
        "treinador", "avançado", "caixas", "boosters", "avulso",
    }
    parts = name.split("-")
    if len(parts) > 1:
        return parts[-1].strip()
    words = name.split()
    filtered = [w for w in words if w.lower() not in ignore and len(w) > 2]
    return " ".join(filtered[:4]) if filtered else name


def _debug_html(html: str) -> None:
    global _debug_done
    if _debug_done:
        return
    _debug_done = True
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string if soup.title else "NO TITLE"
    print(f"[DEBUG] title: {title}")
    all_classes: set = set()
    for el in soup.find_all(True):
        for cls in (el.get("class") or []):
            all_classes.add(cls)
    interesting = sorted(c for c in all_classes if any(
        k in c.lower() for k in ["prod", "card", "item", "price", "preco", "name", "nom", "result"]
    ))
    print(f"[DEBUG] classes: {interesting[:50]}")
    body = soup.find("body")
    print(f"[DEBUG] html[:3000]:\n{str(body)[:3000]}")


def _is_challenge(html: str) -> bool:
    return (
        "cf-turnstile" in html
        or "verificação de segurança" in html.lower()
        or "just a moment" in html.lower()
        or "enable javascript" in html.lower()
    )


def _parse_page(html: str, category: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    products = []
    now = datetime.utcnow().isoformat()

    cards = (
        soup.select(".card-produto")
        or soup.select(".produto-item")
        or soup.select(".product-item")
        or soup.select("li.item")
        or soup.select("[class*='produto']")
        or soup.select("[class*='product']")
        or soup.select(".result-item")
        or soup.select(".search-item")
    )

    if not cards:
        candidates = []
        for el in soup.find_all(["div", "article", "li"]):
            if "R$" in el.get_text():
                children_with_price = [
                    c for c in el.find_all(["div", "article", "li"])
                    if "R$" in c.get_text()
                ]
                if not children_with_price:
                    candidates.append(el)
        if candidates:
            print(f"  [parse] fallback: {len(candidates)} R$-containing elements")
            cards = candidates[:60]

    if not cards:
        _debug_html(html)
        return products

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
            price_el = (
                card.select_one(".preco-por")
                or card.select_one(".price-box .price")
                or card.select_one("[class*='preco']")
                or card.select_one("[class*='price']")
            )
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
                img = (
                    img_el.get("src")
                    or img_el.get("data-src")
                    or img_el.get("data-lazy-src")
                    or ""
                )

            stock_el = (
                card.select_one(".estoque")
                or card.select_one("[class*='stock']")
                or card.select_one("[class*='estoque']")
            )
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


async def scrape() -> list:
    all_products: dict = {}

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
            for page_num in range(1, 11):
                url = _page_url(base_url, page_num)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()

                    if _is_challenge(html):
                        print(f"  page {page_num}: Cloudflare challenge (IP bloqueado neste ambiente)")
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
                    await asyncio.sleep(1.5)

                except Exception as e:
                    print(f"  page {page_num}: error — {e}")
                    break

        await context.close()
        await browser.close()

    return list(all_products.values())


def save_to_kv(products: list, scraped_at: str) -> bool:
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


async def main() -> None:
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
