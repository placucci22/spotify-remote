"""
Vercel serverless entry point — security-hardened FastAPI app.
"""
import sys
import os
import re
import signal
from datetime import datetime
from typing import Optional

# Add api/ directory to path so scrapers/ and services/ are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from scrapers.liga_pokemon import scrape_products
from scrapers.tcgplayer import get_price_for_product_name
from scrapers.price_charting import get_sealed_price_and_trend
from services.exchange_rate import get_usd_brl, usd_to_brl_direct
from services.ev_calculator import calculate_ev, STATIC_EV_DATA
from services.kv_store import kv_get_products, kv_set_products, kv_get_cards
from services.pokeprice import (
    get_sealed_price as pokeprice_sealed,
    get_card_price as pokeprice_card,
    get_top_cards_for_set as pokeprice_set_top,
    get_sets as pokeprice_sets,
    normalize_product_name as pokeprice_normalize,
)

# ──────────────────────────────────────────────
# App + Security middleware
# ──────────────────────────────────────────────

app = FastAPI(
    title="Pokemon Price Dashboard",
    version="1.0.0",
    # Never expose internal error details in production
    docs_url=None if os.getenv("VERCEL_ENV") == "production" else "/docs",
    redoc_url=None,
)

# CORS: localhost for dev; same-origin on Vercel (no CORS needed there,
# but we allow the deployment URL so preview branches work too).
_vercel_url = os.getenv("VERCEL_URL")  # set automatically by Vercel
_allowed_origins = ["http://localhost:5173", "http://localhost:3000"]
if _vercel_url:
    _allowed_origins.append(f"https://{_vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,           # we use no cookies
    allow_methods=["GET", "POST"],     # only what we actually use
    allow_headers=["Content-Type", "Accept"],
)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Never leak stack traces to the client."""
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ──────────────────────────────────────────────
# Input validation helpers
# ──────────────────────────────────────────────

ALLOWED_CATEGORIES = {"booster_box", "etb", "tin", "blister", "collection", "sealed", "accessory", ""}

# Keywords that identify non-booster products (accessories, empty boxes, etc.)
_NON_BOOSTER_KEYWORDS = frozenset([
    "caixa vazia", "pasta", "sleeve", "protetor", "dado", "play mat",
    "tapete", "deck box", "acessório", "storage",
])


def _is_booster_product(product: dict) -> bool:
    """Return False for accessories and non-booster items that would skew EV."""
    if product.get("category") == "accessory":
        return False
    name_lower = product.get("name", "").lower()
    return not any(kw in name_lower for kw in _NON_BOOSTER_KEYWORDS)

_HTML_RE = re.compile(r"<[^>]+>")
_UNSAFE_RE = re.compile(r"[;<>`$\\]")


def _sanitize(value: Optional[str], max_len: int = 120) -> Optional[str]:
    if not value:
        return value
    clean = _HTML_RE.sub("", value)
    clean = _UNSAFE_RE.sub("", clean)
    return clean[:max_len].strip() or None


def _validate_category(cat: Optional[str]) -> Optional[str]:
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Categoria inválida")
    return cat or None


def _validate_product_id(pid: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", pid):
        raise HTTPException(status_code=400, detail="ID de produto inválido")
    return pid


# ──────────────────────────────────────────────
# Demo data (must be defined before cache init)
# ──────────────────────────────────────────────

def _get_demo_products() -> list[dict]:
    now = datetime.now().isoformat()
    return [
        {"id": "demo-001", "name": "Booster Box Scarlet & Violet 151", "url": "https://www.ligapokemon.com.br", "price_brl": 890.0, "category": "booster_box", "set_name": "Scarlet & Violet 151", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-002", "name": "Booster Box Paradox Rift", "url": "https://www.ligapokemon.com.br", "price_brl": 650.0, "category": "booster_box", "set_name": "Paradox Rift", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-003", "name": "Booster Box Temporal Forces", "url": "https://www.ligapokemon.com.br", "price_brl": 720.0, "category": "booster_box", "set_name": "Temporal Forces", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-004", "name": "Booster Box Twilight Masquerade", "url": "https://www.ligapokemon.com.br", "price_brl": 680.0, "category": "booster_box", "set_name": "Twilight Masquerade", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-005", "name": "Booster Box Stellar Crown", "url": "https://www.ligapokemon.com.br", "price_brl": 660.0, "category": "booster_box", "set_name": "Stellar Crown", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-006", "name": "Booster Box Surging Sparks", "url": "https://www.ligapokemon.com.br", "price_brl": 750.0, "category": "booster_box", "set_name": "Surging Sparks", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-007", "name": "Booster Box Prismatic Evolutions", "url": "https://www.ligapokemon.com.br", "price_brl": 1400.0, "category": "booster_box", "set_name": "Prismatic Evolutions", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-008", "name": "Booster Box Journey Together", "url": "https://www.ligapokemon.com.br", "price_brl": 820.0, "category": "booster_box", "set_name": "Journey Together", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-009", "name": "Elite Trainer Box Scarlet & Violet 151", "url": "https://www.ligapokemon.com.br", "price_brl": 320.0, "category": "etb", "set_name": "Scarlet & Violet 151", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-010", "name": "Elite Trainer Box Prismatic Evolutions", "url": "https://www.ligapokemon.com.br", "price_brl": 480.0, "category": "etb", "set_name": "Prismatic Evolutions", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-011", "name": "Elite Trainer Box Surging Sparks", "url": "https://www.ligapokemon.com.br", "price_brl": 290.0, "category": "etb", "set_name": "Surging Sparks", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-012", "name": "Elite Trainer Box Temporal Forces", "url": "https://www.ligapokemon.com.br", "price_brl": 270.0, "category": "etb", "set_name": "Temporal Forces", "image_url": None, "in_stock": False, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-013", "name": "Booster Box Paldea Evolved", "url": "https://www.ligapokemon.com.br", "price_brl": 580.0, "category": "booster_box", "set_name": "Paldea Evolved", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-014", "name": "Tin Pikachu ex", "url": "https://www.ligapokemon.com.br", "price_brl": 180.0, "category": "tin", "set_name": "Scarlet & Violet", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
        {"id": "demo-015", "name": "Tin Charizard ex", "url": "https://www.ligapokemon.com.br", "price_brl": 195.0, "category": "tin", "set_name": "Scarlet & Violet", "image_url": None, "in_stock": True, "seller": "Liga Pokémon", "scraped_at": now},
    ]


# ──────────────────────────────────────────────
# In-memory cache — loaded from KV on first request
# ──────────────────────────────────────────────

_products_cache: list[dict] = _get_demo_products()
_last_scrape: Optional[str] = None
_kv_loaded: bool = False


def _ensure_kv_loaded():
    """Load products from KV once per container lifetime."""
    global _products_cache, _last_scrape, _kv_loaded
    if _kv_loaded:
        return
    _kv_loaded = True
    data = kv_get_products()
    if data and data.get("products"):
        _products_cache = data["products"]
        _last_scrape = data.get("scraped_at")
        print(f"[cache] Loaded {len(_products_cache)} products from KV")


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/api/exchange-rate")
def exchange_rate():
    rate = get_usd_brl()
    return {"usd_brl": rate, "source": "BCB/Fallback", "updated_at": datetime.now().isoformat()}


@app.get("/api/products")
def get_products(
    category: Optional[str] = Query(None, max_length=32),
    in_stock_only: bool = False,
    min_price: Optional[float] = Query(None, ge=0, le=1_000_000),
    max_price: Optional[float] = Query(None, ge=0, le=1_000_000),
    search: Optional[str] = Query(None, max_length=120),
):
    _ensure_kv_loaded()
    category = _validate_category(category)
    search = _sanitize(search)

    products = list(_products_cache)
    if category:
        products = [p for p in products if p.get("category") == category]
    if in_stock_only:
        products = [p for p in products if p.get("in_stock", True)]
    if min_price is not None:
        products = [p for p in products if p.get("price_brl", 0) >= min_price]
    if max_price is not None:
        products = [p for p in products if p.get("price_brl", 0) <= max_price]
    if search:
        s = search.lower()
        products = [p for p in products if s in p.get("name", "").lower()]

    return {"products": products, "total": len(products), "last_updated": _last_scrape}


@app.post("/api/products/refresh")
def refresh_products():
    """
    Trigger a fresh scrape of Liga Pokémon.
    On Vercel serverless each request is ephemeral, so we scrape inline
    with an 8-second timeout then return whatever we found.
    """
    global _products_cache, _last_scrape
    try:
        def _timeout_handler(signum, frame):
            raise TimeoutError

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(8)
        products = scrape_products(max_pages=2)
        signal.alarm(0)
        if products:
            _products_cache = products
            _last_scrape = datetime.now().isoformat()
            return {"message": f"OK — {len(products)} produtos encontrados.", "total": len(products)}
    except (TimeoutError, Exception):
        signal.alarm(0)
    return {"message": "Timeout ou erro no scraping. Dados de demo em uso.", "total": len(_products_cache)}


@app.get("/api/products/{product_id}/analysis")
def product_analysis(product_id: str):
    product_id = _validate_product_id(product_id)
    product = next((p for p in _products_cache if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    rate = get_usd_brl()
    tcg_usd = get_price_for_product_name(product["name"])
    tcg_brl = usd_to_brl_direct(tcg_usd, rate) if tcg_usd else None
    savings = round(((tcg_brl - product["price_brl"]) / tcg_brl) * 100, 1) if tcg_brl else None
    ev = calculate_ev(product["name"], product["price_brl"])
    return {
        "product": product,
        "tcgplayer_usd": tcg_usd,
        "tcgplayer_brl": tcg_brl,
        "savings_pct": savings,
        "ev_analysis": ev,
    }


@app.get("/api/compare")
def compare_products(
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = Query(None, max_length=32),
):
    _ensure_kv_loaded()
    category = _validate_category(category)
    rate = get_usd_brl()
    products = _products_cache
    if category:
        products = [p for p in products if p.get("category") == category]

    # Exclude accessories and non-booster items
    products = [p for p in products if _is_booster_product(p)]

    results = []
    for product in products[:limit]:
        name = product["name"]
        _, lang = pokeprice_normalize(name)
        if lang in ("jp", "cn"):
            continue
        price_brl = product["price_brl"]

        # Try pokeprice first (better PT→EN mapping), fall back to tcgplayer
        usd_price = pokeprice_sealed(name) or get_price_for_product_name(name)
        price_source = "pokeprice" if pokeprice_sealed(name) else ("tcgplayer" if usd_price else None)
        usd_brl = usd_to_brl_direct(usd_price, rate) if usd_price else None
        savings_pct = None
        if usd_brl:
            savings_pct = round(((usd_brl - price_brl) / usd_brl) * 100, 1)

        results.append({
            "id": product["id"],
            "name": name,
            "price_brl": price_brl,
            "usa_price_usd": usd_price,
            "usa_price_brl": usd_brl,
            "savings_pct": savings_pct,
            "is_good_deal": (savings_pct or 0) > 5,
            "recommendation": _price_label(savings_pct),
            "source": price_source,
        })

    results.sort(key=lambda x: x.get("savings_pct") or -999, reverse=True)
    return {"comparisons": results, "exchange_rate": rate}


@app.get("/api/ev")
def ev_analysis(
    category: Optional[str] = Query(None, max_length=32),
    limit: int = Query(20, ge=1, le=50),
):
    _ensure_kv_loaded()
    category = _validate_category(category)
    products = _products_cache
    if category:
        products = [p for p in products if p.get("category") == category]

    sealed_categories = {"booster_box", "etb", "sealed", "blister"}
    sealed = [
        p for p in products
        if p.get("category") in sealed_categories and _is_booster_product(p)
    ]

    results = []
    for product in sealed[:limit]:
        ev = calculate_ev(product["name"], product["price_brl"])
        ev["product_id"] = product["id"]
        ev["product_name"] = product["name"]
        ev["price_brl"] = product["price_brl"]
        ev["image_url"] = product.get("image_url")
        results.append(ev)

    results.sort(key=lambda x: x.get("expected_profit_loss_pct", -999), reverse=True)
    return {"ev_analyses": results}


@app.get("/api/ev/sets")
def ev_known_sets():
    rate = get_usd_brl()
    results = []
    for set_name, data in STATIC_EV_DATA.items():
        ev_usd = data["ev_per_box_usd"]
        results.append({
            "set_name": set_name.title(),
            "ev_per_box_usd": ev_usd,
            "ev_per_box_brl": round(ev_usd * rate, 2),
            "top_hits": data["top_hits"][:5],
        })
    return {"sets": results, "exchange_rate": rate}


@app.get("/api/dashboard")
def dashboard():
    _ensure_kv_loaded()
    rate = get_usd_brl()
    products = _products_cache
    sealed_categories = {"booster_box", "etb", "sealed"}
    sealed = [
        p for p in products
        if p.get("category") in sealed_categories and _is_booster_product(p)
    ]

    ev_list = []
    for p in sealed:
        ev = calculate_ev(p["name"], p["price_brl"])
        ev_list.append({**p, **ev})
    ev_list.sort(key=lambda x: x.get("expected_profit_loss_pct", -999), reverse=True)

    return {
        "exchange_rate": rate,
        "total_products": len(products),
        "total_sealed": len(sealed),
        "best_ev_boxes": ev_list[:12],
        "last_updated": _last_scrape or datetime.now().isoformat(),
    }


@app.get("/api/cards")
def get_cards(
    language: Optional[str] = Query(None, max_length=10),
    set_name: Optional[str] = Query(None, max_length=120),
    rarity: Optional[str] = Query(None, max_length=60),
    search: Optional[str] = Query(None, max_length=120),
    min_price: Optional[float] = Query(None, ge=0, le=1_000_000),
    sort_by: str = Query("price_brl", max_length=20),
    limit: int = Query(200, ge=1, le=500),
):
    data = kv_get_cards()
    if not data or not data.get("cards"):
        return {"cards": [], "total": 0, "last_updated": None, "message": "Sem dados de cartas. Execute o scraper local."}

    cards = data["cards"]
    search = _sanitize(search)
    set_name = _sanitize(set_name)
    rarity = _sanitize(rarity)

    # Filters
    if language:
        lang_lower = language.lower()
        cards = [c for c in cards if c.get("language", "").lower() == lang_lower]
    if set_name:
        s = set_name.lower()
        cards = [c for c in cards if s in c.get("set_name", "").lower()]
    if rarity:
        r = rarity.lower()
        cards = [c for c in cards if r in c.get("rarity", "").lower()]
    if search:
        s = search.lower()
        cards = [c for c in cards if s in c.get("name", "").lower()]
    if min_price is not None:
        cards = [c for c in cards if c.get("price_brl", 0) >= min_price]

    # Sort
    reverse = sort_by not in ("name", "set_name", "rarity")
    key_map = {
        "price_brl": lambda c: c.get("price_brl", 0),
        "name": lambda c: c.get("name", ""),
        "set_name": lambda c: c.get("set_name", ""),
        "rarity": lambda c: c.get("rarity", ""),
    }
    sort_fn = key_map.get(sort_by, key_map["price_brl"])
    cards = sorted(cards, key=sort_fn, reverse=reverse)

    sets = sorted({c.get("set_name", "") for c in data["cards"] if c.get("language", "en") == "en"})
    rarities = sorted({c.get("rarity", "") for c in data["cards"] if c.get("rarity")})

    return {
        "cards": cards[:limit],
        "total": len(cards),
        "last_updated": data.get("scraped_at"),
        "available_sets": sets,
        "available_rarities": rarities,
    }


@app.get("/api/cards/pokeprice")
def cards_pokeprice(
    set_name: Optional[str] = Query(None, max_length=120),
    search: Optional[str] = Query(None, max_length=120),
    language: str = Query("english", max_length=20),
    limit: int = Query(20, ge=1, le=50),
    sort_by: str = Query("price", max_length=20),
):
    """
    Live card prices from PokemonPriceTracker.
    Costs credits — results are cached in-memory per container lifetime.
    Use sparingly: free tier = 100 credits/day.
    """
    set_name = _sanitize(set_name)
    search = _sanitize(search)
    if not set_name and not search:
        raise HTTPException(status_code=400, detail="Forneça 'set_name' ou 'search'")

    from services.pokeprice import _get, _extract_price
    params: dict = {"language": language, "limit": limit, "sortBy": sort_by, "sortOrder": "desc"}
    if set_name:
        params["set"] = set_name
    if search:
        params["search"] = search

    data = _get("cards", params)
    if not data:
        return {"cards": [], "source": "pokeprice", "error": "API indisponível ou sem créditos"}

    raw = data if isinstance(data, list) else data.get("cards", data.get("data", []))
    rate = get_usd_brl()
    cards = []
    for c in raw:
        usd = _extract_price(c)
        cards.append({
            "name": c.get("name", ""),
            "set": c.get("set", set_name or ""),
            "number": c.get("number", ""),
            "rarity": c.get("rarity", ""),
            "language": language,
            "price_usd": usd,
            "price_brl": round(usd * rate, 2) if usd else None,
        })
    return {"cards": cards, "total": len(cards), "exchange_rate": rate, "source": "pokeprice"}


@app.get("/api/trends/{product_name}")
def product_trend(product_name: str):
    name = _sanitize(product_name, max_len=120)
    if not name:
        raise HTTPException(status_code=400, detail="Nome inválido")
    return get_sealed_price_and_trend(name)


@app.get("/api/cron/scrape")
def cron_scrape(request: Request):
    """
    Daily cron endpoint — triggered by Vercel at 06:00 BRT.
    Validates the CRON_SECRET Vercel injects automatically.
    """
    cron_secret = os.getenv("CRON_SECRET", "")
    if cron_secret:
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {cron_secret}":
            raise HTTPException(status_code=401)

    global _products_cache, _last_scrape, _kv_loaded

    try:
        # Scraping is done by GitHub Actions (Playwright) and stored in KV.
        # This endpoint is kept for manual on-demand refresh (lightweight).
        products = scrape_products(max_pages=2)
        if not products:
            return {"ok": False, "message": "Scraping retornou 0 produtos — use o GitHub Actions workflow para scrape completo"}

        scraped_at = datetime.now().isoformat()
        saved = kv_set_products(products, scraped_at)

        _products_cache = products
        _last_scrape = scraped_at
        _kv_loaded = True

        return {
            "ok": True,
            "total": len(products),
            "scraped_at": scraped_at,
            "kv_saved": saved,
        }
    except Exception as e:
        print(f"[cron] Error: {e}")
        return {"ok": False, "message": "Erro durante scraping", "detail": str(e)}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _price_label(savings_pct: Optional[float]) -> str:
    if savings_pct is None:
        return "Sem dados EUA"
    if savings_pct > 20:
        return "ÓTIMO NEGÓCIO"
    if savings_pct > 5:
        return "BOM NEGÓCIO"
    if savings_pct > -5:
        return "PREÇO JUSTO"
    if savings_pct > -20:
        return "LIGEIRAMENTE CARO"
    return "CARO"


# Vercel handler
handler = Mangum(app, lifespan="off")
