"""
Liga Pokémon scraper — NOT used on Vercel.
Scraping runs on a local Mac via scripts/scrape_liga.py (Playwright).
Data is stored in Upstash Redis and read by kv_store.py.
"""


def scrape_products(max_pages: int = 3) -> list:
    """No-op on Vercel — products come from KV (populated by local Mac scraper)."""
    return []
