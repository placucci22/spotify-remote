"""
Pokemon Price Dashboard - FastAPI Backend
Serves price data, comparisons, and EV analysis for the React frontend.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
import asyncio

from database import init_db, get_db, ProductDB, USPriceDB, ExchangeRateDB
from scrapers.liga_pokemon import scrape_products
from scrapers.tcgplayer import get_price_for_product_name
from scrapers.price_charting import get_sealed_price_and_trend
from services.exchange_rate import get_usd_brl, effective_import_cost_brl, BRAZIL_IMPORT_TAX_FACTOR
from services.ev_calculator import calculate_ev, STATIC_EV_DATA
from services.analyzer import analyze_product, rank_products

app = FastAPI(title="Pokemon Price Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache
_products_cache: list[dict] = []
_last_scrape: Optional[datetime] = None
SCRAPE_INTERVAL_SECONDS = 3600  # 1 hour


@app.on_event("startup")
async def startup():
    init_db()
    # Seed with demo products so the dashboard is useful immediately
    global _products_cache
    _products_cache = _get_demo_products()


# ──────────────────────────────────────────────
# Exchange Rate
# ──────────────────────────────────────────────

@app.get("/api/exchange-rate")
def exchange_rate():
    rate = get_usd_brl()
    return {"usd_brl": rate, "source": "BCB/Fallback", "updated_at": datetime.now().isoformat()}


# ──────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────

@app.get("/api/products")
def get_products(
    category: Optional[str] = None,
    in_stock_only: bool = False,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
):
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
async def refresh_products(background_tasks: BackgroundTasks):
    """Trigger a fresh scrape of Liga Pokémon."""
    background_tasks.add_task(_scrape_and_cache)
    return {"message": "Scraping iniciado em background. Aguarde ~30 segundos."}


@app.get("/api/products/{product_id}/analysis")
def product_analysis(product_id: str):
    product = next((p for p in _products_cache if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return analyze_product(product)


# ──────────────────────────────────────────────
# Comparisons
# ──────────────────────────────────────────────

@app.get("/api/compare")
def compare_products(
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
):
    """Compare Liga Pokémon prices with US market prices."""
    rate = get_usd_brl()
    products = _products_cache
    if category:
        products = [p for p in products if p.get("category") == category]

    results = []
    for product in products[:limit]:
        name = product["name"]
        price_brl = product["price_brl"]

        tcgplayer_usd = get_price_for_product_name(name)
        import_cost = effective_import_cost_brl(tcgplayer_usd, rate) if tcgplayer_usd else None

        savings_pct = None
        if import_cost:
            savings_pct = round(((import_cost - price_brl) / import_cost) * 100, 1)

        results.append({
            "id": product["id"],
            "name": name,
            "price_brl": price_brl,
            "tcgplayer_usd": tcgplayer_usd,
            "tcgplayer_brl": round(tcgplayer_usd * rate, 2) if tcgplayer_usd else None,
            "import_cost_brl": import_cost,
            "import_tax_factor": BRAZIL_IMPORT_TAX_FACTOR,
            "savings_pct": savings_pct,
            "is_good_deal": (savings_pct or 0) > 5,
            "recommendation": _price_label(savings_pct),
        })

    results.sort(key=lambda x: x.get("savings_pct") or -999, reverse=True)
    return {"comparisons": results, "exchange_rate": rate}


# ──────────────────────────────────────────────
# EV Analysis
# ──────────────────────────────────────────────

@app.get("/api/ev")
def ev_analysis(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Return EV analysis for all sealed products."""
    products = _products_cache
    if category:
        products = [p for p in products if p.get("category") == category]

    sealed_categories = {"booster_box", "etb", "sealed", "blister"}
    sealed = [p for p in products if p.get("category") in sealed_categories]

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
    """Return EV data for all known sets (using static data)."""
    rate = get_usd_brl()
    results = []
    for set_name, data in STATIC_EV_DATA.items():
        ev_usd = data["ev_per_box_usd"]
        ev_brl = round(ev_usd * rate, 2)
        results.append({
            "set_name": set_name.title(),
            "ev_per_box_usd": ev_usd,
            "ev_per_box_brl": ev_brl,
            "top_hits": data["top_hits"][:5],
        })
    return {"sets": results, "exchange_rate": rate}


# ──────────────────────────────────────────────
# Dashboard summary
# ──────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    """Top-level dashboard data."""
    rate = get_usd_brl()
    products = _products_cache
    sealed = [p for p in products if p.get("category") in {"booster_box", "etb", "sealed"}]

    # Best deals by price vs import
    best_deals = []
    for p in sealed[:10]:
        tcg_usd = get_price_for_product_name(p["name"])
        if tcg_usd:
            import_cost = effective_import_cost_brl(tcg_usd, rate)
            savings = ((import_cost - p["price_brl"]) / import_cost) * 100
            best_deals.append({**p, "savings_pct": round(savings, 1), "tcgplayer_usd": tcg_usd})

    best_deals.sort(key=lambda x: x.get("savings_pct", -999), reverse=True)

    # Best EV boxes
    ev_list = []
    for p in sealed[:10]:
        ev = calculate_ev(p["name"], p["price_brl"])
        ev_list.append({**p, **ev})
    ev_list.sort(key=lambda x: x.get("expected_profit_loss_pct", -999), reverse=True)

    return {
        "exchange_rate": rate,
        "total_products": len(products),
        "total_sealed": len(sealed),
        "best_deals": best_deals[:5],
        "best_ev_boxes": ev_list[:5],
        "last_updated": _last_scrape or datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────
# Trend data
# ──────────────────────────────────────────────

@app.get("/api/trends/{product_name}")
def product_trend(product_name: str):
    return get_sealed_price_and_trend(product_name)


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


async def _scrape_and_cache():
    global _products_cache, _last_scrape
    try:
        products = scrape_products(max_pages=3)
        if products:
            _products_cache = products
        _last_scrape = datetime.now()
        print(f"[scraper] Scraped {len(products)} products")
    except Exception as e:
        print(f"[scraper] Error: {e}")


def _get_demo_products() -> list[dict]:
    """
    Seed data so the dashboard is immediately useful.
    These are typical Liga Pokémon prices — refresh to get live data.
    """
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
