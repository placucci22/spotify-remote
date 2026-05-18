"""Quick diagnostic: load one page and save full HTML to file for inspection."""
from __future__ import annotations
import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from playwright.async_api import async_playwright

URL = "https://www.ligapokemon.com.br/?view=cards/search&card=categ%3D10+searchprod%3D1"
OUT = Path.home() / "liga_debug.html"


async def main():
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

        print(f"Loading {URL} ...")
        await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)

        # Try to wait for actual product content
        try:
            await page.wait_for_selector(
                "[class*='produto'], [class*='product'], .card, .item, article",
                timeout=8_000
            )
            print("Product selector found!")
        except Exception:
            print("Product selector timeout — saving what we have")
            await page.wait_for_timeout(5_000)

        html = await page.content()
        OUT.write_text(html, encoding="utf-8")
        print(f"Saved {len(html):,} chars to {OUT}")

        # Print a relevant excerpt (search for product-like content)
        lower = html.lower()
        for keyword in ["produto", "product", "preco", "price", "booster"]:
            idx = lower.find(keyword)
            if idx != -1:
                start = max(0, idx - 200)
                print(f"\n--- context around '{keyword}' (pos {idx}) ---")
                print(html[start:idx + 500])
                break

        await browser.close()


asyncio.run(main())
