from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Product(BaseModel):
    id: str
    name: str
    url: str
    price_brl: float
    category: str
    set_name: Optional[str] = None
    image_url: Optional[str] = None
    in_stock: bool = True
    seller: Optional[str] = None
    scraped_at: datetime = datetime.now()


class USPrice(BaseModel):
    product_name: str
    tcgplayer_price_usd: Optional[float] = None
    pokemon_center_price_usd: Optional[float] = None
    pricecharting_sealed_usd: Optional[float] = None
    pricecharting_used_usd: Optional[float] = None


class ExchangeRate(BaseModel):
    usd_brl: float
    source: str
    updated_at: datetime


class PriceComparison(BaseModel):
    product_name: str
    price_brl: float
    us_price_usd: Optional[float]
    us_price_brl: Optional[float]
    exchange_rate: float
    import_tax_factor: float = 1.60  # ~60% import tax in Brazil
    effective_import_cost_brl: Optional[float]
    is_cheaper_in_br: Optional[bool]
    savings_percentage: Optional[float]
    recommendation: str


class CardHit(BaseModel):
    name: str
    rarity: str
    tcgplayer_price_usd: float
    pull_rate: float  # cards per box


class EVAnalysis(BaseModel):
    set_name: str
    box_price_brl: float
    box_price_usd: Optional[float]
    packs_per_box: int
    pack_price_brl: float
    ev_per_box_usd: float
    ev_per_box_brl: float
    expected_profit_loss_brl: float
    expected_profit_loss_pct: float
    notable_pulls: list[CardHit]
    sealed_trend: str  # "INCREASING" | "DECREASING" | "STABLE"
    sealed_pricecharting_30d_change_pct: Optional[float]
    recommendation: str  # "OPEN" | "KEEP_SEALED" | "AVOID" | "BUY_AND_HOLD"
    recommendation_reason: str


class DashboardStats(BaseModel):
    total_products: int
    best_deals: list[PriceComparison]
    best_ev_boxes: list[EVAnalysis]
    exchange_rate: float
    last_updated: datetime
