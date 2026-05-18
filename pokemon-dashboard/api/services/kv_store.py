"""
Vercel KV (Upstash Redis) client for persisting scraped product data.
Env vars injected automatically when you link a KV store in the Vercel dashboard:
  KV_REST_API_URL, KV_REST_API_TOKEN
Falls back gracefully (returns None) when those vars are absent.
"""
import os
import json
import requests
from typing import Optional

# Upstash via Vercel Marketplace injects UPSTASH_REDIS_REST_URL / TOKEN
# Legacy Vercel KV used KV_REST_API_URL / TOKEN — support both
_KV_URL = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL", "")
_KV_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN", "")

PRODUCTS_KEY = "liga_products_v1"
PRODUCTS_TTL = 90_000  # 25 hours in seconds


def _available() -> bool:
    return bool(_KV_URL and _KV_TOKEN)


def _headers() -> dict:
    return {"Authorization": f"Bearer {_KV_TOKEN}"}


def kv_get_products() -> Optional[dict]:
    """Return {"products": [...], "scraped_at": "..."} or None."""
    if not _available():
        return None
    try:
        r = requests.get(
            f"{_KV_URL}/get/{PRODUCTS_KEY}",
            headers=_headers(),
            timeout=5,
        )
        result = r.json().get("result")
        if result:
            return json.loads(result)
    except Exception as e:
        print(f"[kv_store] get error: {e}")
    return None


def kv_set_products(products: list, scraped_at: str) -> bool:
    """Store products in KV with a 25h TTL. Returns True on success."""
    if not _available():
        return False
    try:
        payload = json.dumps({"products": products, "scraped_at": scraped_at}, ensure_ascii=False)
        r = requests.post(
            f"{_KV_URL}/pipeline",
            json=[["SET", PRODUCTS_KEY, payload, "EX", str(PRODUCTS_TTL)]],
            headers={**_headers(), "Content-Type": "application/json"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[kv_store] set error: {e}")
        return False
