"""
Main analysis service: combines Liga Pokémon prices, US prices,
exchange rates, and EV data to produce buy/hold/avoid recommendations.
"""
from services.exchange_rate import get_usd_brl, effective_import_cost_brl, BRAZIL_IMPORT_TAX_FACTOR
from services.ev_calculator import calculate_ev
from scrapers.tcgplayer import get_price_for_product_name
from scrapers.price_charting import get_sealed_price_and_trend
from typing import Optional


def analyze_product(product: dict) -> dict:
    """
    Full analysis of a Liga Pokémon product.
    Returns comparison + EV + recommendation.
    """
    rate = get_usd_brl()
    price_brl = product["price_brl"]
    name = product["name"]
    category = product.get("category", "sealed")

    # Fetch US prices
    tcgplayer_usd = get_price_for_product_name(name)
    pc_data = get_sealed_price_and_trend(name)
    pricecharting_usd = pc_data.get("sealed_usd")
    trend = pc_data.get("trend", "UNKNOWN")
    change_30d = pc_data.get("thirty_day_change_pct")

    # Best US reference price
    us_prices = [p for p in [tcgplayer_usd, pricecharting_usd] if p is not None]
    us_ref_usd = min(us_prices) if us_prices else None

    # What it would cost to import this from the USA to Brazil
    import_cost_brl = effective_import_cost_brl(us_ref_usd, rate) if us_ref_usd else None

    # Is it cheaper in Brazil?
    is_cheaper_in_br = None
    savings_pct = None
    if import_cost_brl:
        is_cheaper_in_br = price_brl < import_cost_brl
        savings_pct = round(((import_cost_brl - price_brl) / import_cost_brl) * 100, 1)

    # EV analysis (only for sealed products)
    ev_data = None
    if category in ("booster_box", "etb", "blister", "sealed"):
        ev_data = calculate_ev(name, price_brl)

    # Overall recommendation
    overall_rec, reason = _overall_recommendation(
        price_brl, us_ref_usd, import_cost_brl, savings_pct, ev_data, trend
    )

    return {
        "product": product,
        "comparison": {
            "price_brl": price_brl,
            "tcgplayer_price_usd": tcgplayer_usd,
            "pricecharting_sealed_usd": pricecharting_usd,
            "us_ref_price_usd": us_ref_usd,
            "us_ref_price_brl": round(us_ref_usd * rate, 2) if us_ref_usd else None,
            "import_cost_with_tax_brl": import_cost_brl,
            "exchange_rate": rate,
            "import_tax_factor": BRAZIL_IMPORT_TAX_FACTOR,
            "is_cheaper_in_br": is_cheaper_in_br,
            "savings_vs_import_pct": savings_pct,
        },
        "ev_analysis": ev_data,
        "trend": {
            "direction": trend,
            "thirty_day_change_pct": change_30d,
        },
        "recommendation": overall_rec,
        "recommendation_reason": reason,
    }


def _overall_recommendation(
    price_brl: float,
    us_ref_usd: Optional[float],
    import_cost_brl: Optional[float],
    savings_pct: Optional[float],
    ev_data: Optional[dict],
    trend: str,
) -> tuple[str, str]:
    reasons = []
    score = 0  # Positive = buy, negative = avoid

    # Price vs import cost factor
    if savings_pct is not None:
        if savings_pct > 20:
            score += 3
            reasons.append(f"muito mais barato que importar ({savings_pct:.0f}% de economia)")
        elif savings_pct > 5:
            score += 1
            reasons.append(f"mais barato que importar ({savings_pct:.0f}% de economia)")
        elif savings_pct < -10:
            score -= 2
            reasons.append(f"mais caro que importar ({-savings_pct:.0f}% acima do custo de importação)")

    # EV factor
    if ev_data:
        ev_rec = ev_data.get("recommendation", "")
        loss_pct = ev_data.get("expected_profit_loss_pct", -100)
        if ev_rec in ("OPEN", "OPEN_OR_SELL"):
            score += 2
            reasons.append("EV favorável para abrir")
        elif ev_rec == "BUY_AND_HOLD":
            score += 2
            reasons.append("selado tende a valorizar")
        elif loss_pct < -40:
            score -= 1
            reasons.append("EV negativo ao abrir")

    # Trend factor
    if trend == "INCREASING":
        score += 2
        reasons.append("tendência de alta nos últimos 30 dias")
    elif trend == "DECREASING":
        score -= 1
        reasons.append("tendência de queda recente")

    # Final verdict
    if score >= 4:
        return "COMPRA FORTE", " | ".join(reasons)
    elif score >= 2:
        return "COMPRA", " | ".join(reasons)
    elif score >= 0:
        return "NEUTRO", " | ".join(reasons) or "Preço justo, sem urgência"
    elif score >= -2:
        return "AGUARDAR", " | ".join(reasons)
    else:
        return "EVITAR", " | ".join(reasons) or "Preço acima do mercado"


def rank_products(analyzed_products: list[dict]) -> list[dict]:
    """Sort products by recommendation strength."""
    order = {"COMPRA FORTE": 0, "COMPRA": 1, "NEUTRO": 2, "AGUARDAR": 3, "EVITAR": 4}
    return sorted(analyzed_products, key=lambda x: order.get(x.get("recommendation", "NEUTRO"), 5))
