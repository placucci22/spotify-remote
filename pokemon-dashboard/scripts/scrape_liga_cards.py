#!/usr/bin/env python3
"""
Playwright scraper for Liga Pokémon single cards — runs locally on Mac.
Targets English (ING) card editions only.

Liga URL for card search by edition:
  https://www.ligapokemon.com.br/?view=cards/search&card=ed=<ABBREV>

Language detection strategy:
- Liga labels sealed products with (PT-BR), (ING), (JAP) prefixes.
- For cards, the edition name shown on the page usually contains the
  language identifier. We filter for editions whose name contains "ING"
  or matches known English set abbreviations.
- Cards from Japanese/PT-BR editions are skipped.

Usage:
    python scripts/scrape_liga_cards.py
    python scripts/scrape_liga_cards.py --sets SVI PAR TWM  # specific sets
    python scripts/scrape_liga_cards.py --min-price 50      # only cards >= R$50
"""
from __future__ import annotations

import asyncio
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Load .env from the same directory as this script (or cwd)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_URL = "https://www.ligapokemon.com.br"
CARD_SEARCH_URL = BASE_URL + "/?view=cards/search&card=ed={abbrev}"
EDITION_LIST_URL = BASE_URL + "/?view=cards/editions"

KV_URL = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN", "")
KV_KEY = "liga_cards_v1"
KV_TTL = 90_000

# Known English (ING) Scarlet & Violet set abbreviations on Liga
# Update this list as new sets are released
ENGLISH_SET_ABBREVS = [
    "SVI",   # Scarlet & Violet Base
    "PAL",   # Paldea Evolved
    "OBF",   # Obsidian Flames
    "MEW",   # 151
    "PAR",   # Paradox Rift
    "PAF",   # Paldean Fates
    "TEF",   # Temporal Forces
    "TWM",   # Twilight Masquerade
    "SHF",   # Shrouded Fable
    "SCR",   # Stellar Crown
    "SSP",   # Surging Sparks
    "PRE",   # Prismatic Evolutions
    "JTG",   # Journey Together
    # Sword & Shield
    "ASR",   # Astral Radiance
    "LOR",   # Lost Origin
    "SIT",   # Silver Tempest
    "CRZ",   # Crown Zenith
    "CRE",   # Chilling Reign
    "EVS",   # Evolving Skies (note: EVS is also PT-BR SV1 on some sites — skip if ambiguous)
    "BST",   # Battle Styles
    "RCL",   # Rebel Clash
    "VIV",   # Vivid Voltage
    "DAA",   # Darkness Ablaze
    "SSH",   # Sword & Shield Base
    "CPA",   # Champion's Path
    "SHF",   # Shining Fates
]

# Rarity keywords that indicate the card is worth tracking
HIGH_VALUE_RARITIES = {
    "special illustration rare", "hyper rare", "illustration rare",
    "ultra rare", "double rare", "secret rare", "full art",
    "rainbow rare", "gold rare", "alternate art",
    # Portuguese equivalents sometimes shown
    "ilustração especial rara", "hiper rara", "ilustração rara",
    "ultra rara", "dupla rara",
}


def _parse_price(text: str) -> float | None:
    cleaned = re.sub(r"[^\d,.]", "", text or "").replace(",", ".")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _detect_language(text: str) -> str:
    """Detect card language from edition name or any visible text."""
    t = text.upper()
    if "ING" in t or "ENG" in t or "EN)" in t:
        return "en"
    if "PT-BR" in t or "PTBR" in t or "PORT" in t:
        return "pt"
    if "JAP" in t or "JPN" in t or "JP)" in t:
        return "jp"
    if "CHN" in t or "CHI" in t:
        return "cn"
    return "en"  # default: assume English for known English set abbreviations


def _card_id(name: str, set_name: str, number: str) -> str:
    key = f"{name}|{set_name}|{number}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _parse_card_page(html: str, set_abbrev: str) -> list[dict]:
    """Parse card search results HTML and return list of card dicts."""
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    now = datetime.utcnow().isoformat()

    # Liga card search shows results in rows or grid items
    # Try multiple selector patterns
    items = (
        soup.select(".card-result")
        or soup.select(".card-produto")
        or soup.select(".card[data-card]")
        or soup.select("tr.card-row")
        or soup.select(".search-result-item")
        or soup.select(".product-card")
    )

    # Fallback: look for table rows if it's a table layout
    if not items:
        table = soup.find("table", class_=re.compile(r"card|result|search", re.I))
        if table:
            items = table.find_all("tr")[1:]  # skip header row

    for item in items:
        text = item.get_text(" ", strip=True)
        if not text:
            continue

        # Card name
        name_el = (
            item.find(class_=re.compile(r"name|title|card-name", re.I))
            or item.find("a")
            or item.find("h5")
            or item.find("h6")
        )
        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            continue

        # Price — look for BRL price element
        price_el = (
            item.find(class_=re.compile(r"price|preco|valor", re.I))
            or item.find(string=re.compile(r"R\$"))
        )
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_brl = _parse_price(price_text)

        # Card number (e.g. "123/198")
        number_match = re.search(r"\b(\d{1,3}/\d{1,3})\b", text)
        card_number = number_match.group(1) if number_match else ""

        # Rarity
        rarity_el = item.find(class_=re.compile(r"rarity|raridade", re.I))
        rarity = rarity_el.get_text(strip=True) if rarity_el else ""

        # Set/edition info
        edition_el = item.find(class_=re.compile(r"edition|edicao|set|col", re.I))
        set_name = edition_el.get_text(strip=True) if edition_el else set_abbrev

        # Language detection from the full text of the item
        language = _detect_language(text + " " + set_name)

        # Stock
        out_of_stock = bool(item.find(class_=re.compile(r"esgotado|out.?of.?stock|sold.?out", re.I)))
        in_stock = not out_of_stock and price_brl is not None

        # Card URL
        link = item.find("a", href=True)
        url = BASE_URL + link["href"] if link and link["href"].startswith("/") else (link["href"] if link else "")

        cards.append({
            "id": _card_id(name, set_name, card_number),
            "name": name,
            "set_name": set_name,
            "set_abbrev": set_abbrev,
            "card_number": card_number,
            "rarity": rarity,
            "language": language,
            "price_brl": price_brl,
            "in_stock": in_stock,
            "url": url,
            "scraped_at": now,
        })

    return cards


async def scrape_set(page, abbrev: str, min_price: float = 0, debug: bool = False) -> list[dict]:
    """Scrape all cards for one set abbreviation."""
    url = CARD_SEARCH_URL.format(abbrev=abbrev)
    print(f"[{abbrev}] Fetching {url}")
    cards = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2000)

        # Click through pagination / load-more buttons
        for page_num in range(1, 20):
            html = await page.content()

            if debug and page_num == 1:
                debug_file = f"debug_{abbrev}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"[{abbrev}] HTML salvo em {debug_file} ({len(html)} bytes)")

            batch = _parse_card_page(html, abbrev)
            if not batch and page_num == 1:
                print(f"[{abbrev}] No cards found — check selectors or set abbreviation")
                break

            new_cards = [c for c in batch if c["id"] not in {x["id"] for x in cards}]
            cards.extend(new_cards)

            # Try to find and click a "next page" or "load more" button
            next_btn = await page.query_selector(
                "a.proxima, a[rel='next'], button.load-more, "
                ".pagination .next, [aria-label='Next']"
            )
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_timeout(2000)

    except Exception as e:
        print(f"[{abbrev}] Error: {e}")

    # Filter by price and language
    en_cards = [c for c in cards if c.get("language") == "en"]
    if min_price > 0:
        en_cards = [c for c in en_cards if (c.get("price_brl") or 0) >= min_price]

    print(f"[{abbrev}] Found {len(en_cards)} English cards (total scraped: {len(cards)})")
    return en_cards


def kv_save(cards: list[dict], scraped_at: str) -> None:
    if not KV_URL or not KV_TOKEN:
        print("[kv] No KV credentials — not saving to Redis")
        print(json.dumps({"total": len(cards), "sample": cards[:3]}, ensure_ascii=False, indent=2))
        return
    payload = json.dumps({"cards": cards, "scraped_at": scraped_at}, ensure_ascii=False)
    r = requests.post(
        f"{KV_URL}/pipeline",
        json=[["SET", KV_KEY, payload, "EX", str(KV_TTL)]],
        headers={"Authorization": f"Bearer {KV_TOKEN}", "Content-Type": "application/json"},
        timeout=15,
    )
    if r.status_code == 200:
        print(f"[kv] Saved {len(cards)} cards to Redis (key={KV_KEY})")
    else:
        print(f"[kv] Save failed: {r.status_code} {r.text}")


async def main(sets: list[str], min_price: float, debug: bool = False) -> None:
    all_cards: list[dict] = []
    seen_ids: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})

        for abbrev in sets:
            cards = await scrape_set(page, abbrev, min_price, debug=debug)
            for card in cards:
                if card["id"] not in seen_ids:
                    seen_ids.add(card["id"])
                    all_cards.append(card)

        await browser.close()

    scraped_at = datetime.utcnow().isoformat()
    print(f"\nTotal unique English cards: {len(all_cards)}")

    # Sort by price descending before saving
    all_cards.sort(key=lambda c: c.get("price_brl") or 0, reverse=True)
    kv_save(all_cards, scraped_at)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Liga Pokémon card singles (English only)")
    parser.add_argument("--sets", nargs="+", default=ENGLISH_SET_ABBREVS, metavar="ABBREV",
                        help="Set abbreviations to scrape (default: all known English sets)")
    parser.add_argument("--min-price", type=float, default=0,
                        help="Minimum price in BRL to include (default: 0 = all)")
    parser.add_argument("--debug", action="store_true",
                        help="Save raw HTML to debug_<ABBREV>.html for selector inspection")
    args = parser.parse_args()

    asyncio.run(main(args.sets, args.min_price, debug=args.debug))
