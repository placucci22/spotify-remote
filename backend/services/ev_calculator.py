"""
Expected Value (EV) calculator for Pokemon booster boxes.
Uses TCGPlayer singles prices + known pull rates to estimate box EV.
"""
from services.exchange_rate import convert_usd_to_brl, get_usd_brl
from scrapers.tcgplayer import get_set_singles_prices

# Known booster box configurations
BOX_CONFIGS = {
    "default": {
        "packs_per_box": 36,
        "cards_per_pack": 10,
        "hits_per_box": 18,  # ~1 hit every 2 packs
        "bulk_value_per_pack_usd": 0.45,
    },
    "etb": {
        "packs_per_box": 9,
        "cards_per_pack": 10,
        "hits_per_box": 3,
        "bulk_value_per_pack_usd": 0.45,
    },
    "blister": {
        "packs_per_box": 3,
        "cards_per_pack": 10,
        "hits_per_box": 1,
        "bulk_value_per_pack_usd": 0.45,
    },
}

# Rarity weights for pull rate calculation
RARITY_PULL_RATE = {
    "Special Illustration Rare": 0.15,  # ~1 per 6-7 boxes
    "Hyper Rare": 0.20,
    "Illustration Rare": 0.40,
    "Ultra Rare": 1.5,
    "Double Rare": 3.0,
    "Rare Holo": 6.0,
    "Rare": 6.0,
    "Common": 0,
    "Uncommon": 0,
    "Unknown": 0.5,
}

# Pre-computed EV data for popular sets (USD values from TCGPlayer)
# Updated periodically - serves as cached fallback when scraping fails
STATIC_EV_DATA = {
    "scarlet & violet 151": {
        "set_slug": "scarlet-violet-151",
        "ev_per_box_usd": 95.0,
        "top_hits": [
            {"name": "Charizard ex SAR", "rarity": "Special Illustration Rare", "price_usd": 85.0, "pull_rate": 0.12},
            {"name": "Mew ex SAR", "rarity": "Special Illustration Rare", "price_usd": 35.0, "pull_rate": 0.12},
            {"name": "Blastoise ex SAR", "rarity": "Special Illustration Rare", "price_usd": 20.0, "pull_rate": 0.12},
            {"name": "Charizard ex UR", "rarity": "Ultra Rare", "price_usd": 28.0, "pull_rate": 1.5},
            {"name": "Mew ex UR", "rarity": "Ultra Rare", "price_usd": 12.0, "pull_rate": 1.5},
        ],
    },
    "paradox rift": {
        "set_slug": "paradox-rift",
        "ev_per_box_usd": 70.0,
        "top_hits": [
            {"name": "Iron Valiant ex SAR", "rarity": "Special Illustration Rare", "price_usd": 45.0, "pull_rate": 0.12},
            {"name": "Roaring Moon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 40.0, "pull_rate": 0.12},
            {"name": "Garchomp ex SAR", "rarity": "Special Illustration Rare", "price_usd": 15.0, "pull_rate": 0.12},
        ],
    },
    "temporal forces": {
        "set_slug": "temporal-forces",
        "ev_per_box_usd": 85.0,
        "top_hits": [
            {"name": "Walking Wake ex SAR", "rarity": "Special Illustration Rare", "price_usd": 50.0, "pull_rate": 0.12},
            {"name": "Iron Leaves ex SAR", "rarity": "Special Illustration Rare", "price_usd": 30.0, "pull_rate": 0.12},
            {"name": "Raging Bolt ex SAR", "rarity": "Special Illustration Rare", "price_usd": 25.0, "pull_rate": 0.12},
        ],
    },
    "twilight masquerade": {
        "set_slug": "twilight-masquerade",
        "ev_per_box_usd": 75.0,
        "top_hits": [
            {"name": "Teal Mask Ogerpon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 55.0, "pull_rate": 0.12},
            {"name": "Hearthflame Mask Ogerpon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 30.0, "pull_rate": 0.12},
        ],
    },
    "stellar crown": {
        "set_slug": "stellar-crown",
        "ev_per_box_usd": 72.0,
        "top_hits": [
            {"name": "Terapagos ex SAR", "rarity": "Special Illustration Rare", "price_usd": 60.0, "pull_rate": 0.12},
            {"name": "Stellar Crown Pikachu", "rarity": "Special Illustration Rare", "price_usd": 20.0, "pull_rate": 0.12},
        ],
    },
    "surging sparks": {
        "set_slug": "surging-sparks",
        "ev_per_box_usd": 88.0,
        "top_hits": [
            {"name": "Pikachu ex SAR", "rarity": "Special Illustration Rare", "price_usd": 80.0, "pull_rate": 0.12},
            {"name": "Raichu ex SAR", "rarity": "Special Illustration Rare", "price_usd": 35.0, "pull_rate": 0.12},
        ],
    },
    "prismatic evolutions": {
        "set_slug": "prismatic-evolutions",
        "ev_per_box_usd": 180.0,
        "top_hits": [
            {"name": "Umbreon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 220.0, "pull_rate": 0.12},
            {"name": "Espeon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 85.0, "pull_rate": 0.12},
            {"name": "Vaporeon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 70.0, "pull_rate": 0.12},
            {"name": "Flareon ex SAR", "rarity": "Special Illustration Rare", "price_usd": 60.0, "pull_rate": 0.12},
        ],
    },
    "journey together": {
        "set_slug": "journey-together",
        "ev_per_box_usd": 90.0,
        "top_hits": [
            {"name": "Red SAR", "rarity": "Special Illustration Rare", "price_usd": 75.0, "pull_rate": 0.08},
            {"name": "Blue SAR", "rarity": "Special Illustration Rare", "price_usd": 60.0, "pull_rate": 0.08},
            {"name": "Charizard ex SAR", "rarity": "Special Illustration Rare", "price_usd": 50.0, "pull_rate": 0.08},
        ],
    },
}


def _match_set(product_name: str) -> str:
    """Match a product name to a known set key."""
    name_lower = product_name.lower()
    for key in STATIC_EV_DATA:
        if key in name_lower:
            return key
    # Partial match
    for key in STATIC_EV_DATA:
        words = key.split()
        if sum(1 for w in words if w in name_lower) >= len(words) - 1:
            return key
    return ""


def _categorize_product(product_name: str) -> str:
    name_lower = product_name.lower()
    if any(k in name_lower for k in ["etb", "elite trainer"]):
        return "etb"
    if "blister" in name_lower:
        return "blister"
    return "default"


def calculate_ev(product_name: str, box_price_brl: float, live_fetch: bool = False) -> dict:
    """
    Calculate expected value of opening a booster box.

    Returns a dict with EV data and recommendation.
    """
    rate = get_usd_brl()
    set_key = _match_set(product_name)
    config_key = _categorize_product(product_name)
    config = BOX_CONFIGS[config_key]

    ev_usd = None
    top_hits = []

    if set_key and set_key in STATIC_EV_DATA:
        ev_data = STATIC_EV_DATA[set_key]
        ev_usd = ev_data["ev_per_box_usd"]
        top_hits = ev_data["top_hits"]

        # Scale EV if ETB (fewer packs than booster box)
        if config_key == "etb":
            box_ratio = config["packs_per_box"] / BOX_CONFIGS["default"]["packs_per_box"]
            ev_usd *= box_ratio

    elif live_fetch and set_key:
        ev_usd = _calculate_ev_from_tcgplayer(STATIC_EV_DATA.get(set_key, {}).get("set_slug", set_key), config)

    if ev_usd is None:
        ev_usd = _estimate_ev_from_box_price(box_price_brl, rate)

    ev_brl = convert_usd_to_brl(ev_usd, rate)
    box_price_usd = box_price_brl / rate
    profit_loss_brl = ev_brl - box_price_brl
    profit_loss_pct = (profit_loss_brl / box_price_brl) * 100
    pack_price_brl = box_price_brl / config["packs_per_box"]

    recommendation, reason = _recommend(
        profit_loss_pct, config_key, set_key, product_name
    )

    return {
        "set_name": set_key.title() if set_key else product_name,
        "box_price_brl": box_price_brl,
        "box_price_usd": round(box_price_usd, 2),
        "packs_per_box": config["packs_per_box"],
        "pack_price_brl": round(pack_price_brl, 2),
        "ev_per_box_usd": round(ev_usd, 2),
        "ev_per_box_brl": round(ev_brl, 2),
        "expected_profit_loss_brl": round(profit_loss_brl, 2),
        "expected_profit_loss_pct": round(profit_loss_pct, 1),
        "notable_pulls": top_hits[:5],
        "recommendation": recommendation,
        "recommendation_reason": reason,
    }


def _calculate_ev_from_tcgplayer(set_slug: str, config: dict) -> float:
    """Live EV calculation from TCGPlayer singles prices."""
    cards = get_set_singles_prices(set_slug)
    if not cards:
        return 0.0

    ev = 0.0
    for card in cards:
        rarity = card.get("rarity", "Unknown")
        price = card.get("market_price_usd", 0)
        pull_rate = RARITY_PULL_RATE.get(rarity, 0.5)
        ev += price * (pull_rate / config["packs_per_box"])

    bulk = config["bulk_value_per_pack_usd"] * config["packs_per_box"]
    return ev + bulk


def _estimate_ev_from_box_price(box_price_brl: float, rate: float) -> float:
    """Rough EV estimate when set data is unavailable: assume 70% EV ratio."""
    box_price_usd = box_price_brl / rate
    return box_price_usd * 0.70


def _recommend(profit_loss_pct: float, config_key: str, set_key: str, product_name: str) -> tuple[str, str]:
    """Generate open/keep-sealed recommendation based on EV analysis."""

    # Special cases for known high-value sealed sets
    high_sealed_value_sets = {"prismatic evolutions", "scarlet & violet 151", "surging sparks"}
    if set_key in high_sealed_value_sets:
        return (
            "BUY_AND_HOLD",
            f"Sealed {set_key.title()} has strong appreciation history. EV negativo mas sealed tende a valorizar mais.",
        )

    if profit_loss_pct > 10:
        return (
            "OPEN",
            f"EV positivo (+{profit_loss_pct:.1f}%). Abrir a caixa tem expectativa de lucro!",
        )
    elif profit_loss_pct > -15:
        return (
            "OPEN_OR_SELL",
            f"EV quase neutro ({profit_loss_pct:.1f}%). Pode abrir se quiser diversão, ou vender para lucro seguro.",
        )
    elif profit_loss_pct > -35:
        return (
            "KEEP_SEALED",
            f"EV negativo ({profit_loss_pct:.1f}%). Melhor guardar selado — tende a valorizar mais que o conteúdo.",
        )
    else:
        return (
            "AVOID",
            f"EV muito negativo ({profit_loss_pct:.1f}%). Preço alto demais; procure desconto ou outro produto.",
        )
