"""
Exchange rate service for USD/BRL conversion.
Uses the Brazilian Central Bank API (api.bcb.gov.br) as primary source,
with exchangerate-api.com as fallback.
"""
import requests
from datetime import datetime, timedelta
from typing import Optional

# Brazilian Central Bank - free, no auth required
BCB_API = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{date}'&$format=json&$select=cotacaoVenda"

# Backup free API - no auth required for basic use
EXCHANGERATE_API = "https://api.exchangerate-api.com/v4/latest/USD"

# Cache
_cached_rate: Optional[float] = None
_cache_time: Optional[datetime] = None
CACHE_DURATION = timedelta(hours=2)


def get_usd_brl(force_refresh: bool = False) -> float:
    global _cached_rate, _cache_time

    if (
        not force_refresh
        and _cached_rate is not None
        and _cache_time is not None
        and datetime.now() - _cache_time < CACHE_DURATION
    ):
        return _cached_rate

    rate = _fetch_from_bcb() or _fetch_from_exchangerate_api()

    if rate:
        _cached_rate = rate
        _cache_time = datetime.now()
        return rate

    # Ultimate fallback: use last cached or reasonable default
    if _cached_rate:
        return _cached_rate
    return 5.70  # Conservative fallback if all APIs fail


def _fetch_from_bcb() -> Optional[float]:
    """Fetch USD/BRL rate from Brazilian Central Bank (PTAX)."""
    for days_back in range(0, 5):  # Try up to 5 days back (weekends/holidays)
        date = (datetime.now() - timedelta(days=days_back)).strftime("%m-%d-%Y")
        url = BCB_API.format(date=date)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                values = data.get("value", [])
                if values and values[0].get("cotacaoVenda"):
                    rate = float(values[0]["cotacaoVenda"])
                    print(f"[exchange_rate] BCB rate: {rate} (date: {date})")
                    return rate
        except Exception as e:
            print(f"[exchange_rate] BCB error: {e}")
    return None


def _fetch_from_exchangerate_api() -> Optional[float]:
    """Fallback: fetch from exchangerate-api.com (free tier)."""
    try:
        resp = requests.get(EXCHANGERATE_API, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get("rates", {}).get("BRL")
            if rate:
                print(f"[exchange_rate] ExchangeRate-API rate: {rate}")
                return float(rate)
    except Exception as e:
        print(f"[exchange_rate] ExchangeRate-API error: {e}")
    return None


def convert_usd_to_brl(usd: float, rate: Optional[float] = None) -> float:
    if rate is None:
        rate = get_usd_brl()
    return round(usd * rate, 2)


def convert_brl_to_usd(brl: float, rate: Optional[float] = None) -> float:
    if rate is None:
        rate = get_usd_brl()
    return round(brl / rate, 2)


def usd_to_brl_direct(usd_price: float, rate: Optional[float] = None) -> float:
    """Convert USD price to BRL at the current exchange rate (no taxes applied)."""
    return convert_usd_to_brl(usd_price, rate)
