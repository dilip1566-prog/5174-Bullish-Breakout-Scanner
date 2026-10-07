from typing import Optional
from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    price_gt_sma20: bool
    price_gt_sma50: bool
    price_gt_sma200: bool
    sma20_gt_sma50: bool
    sma50_gt_sma200: bool
    rsi_in_range: bool
    adx_strong: bool
    di_bullish: bool
    rvol_strong: bool
    breakout_confirmed: bool
    near_high: bool
    rs_vs_spy: bool  # worth +2
    total: int
    max_total: int = 13


class ScanResult(BaseModel):
    symbol: str
    name: str
    sector: str
    price: float
    market_cap: Optional[float] = None
    avg_volume: Optional[float] = None

    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    sma50_rising: Optional[bool] = None

    rsi14: Optional[float] = None
    adx14: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None

    consolidation_days: Optional[int] = None
    consolidation_range_pct: Optional[float] = None
    breakout_pct: Optional[float] = None
    pct_from_20d_high: Optional[float] = None
    pct_from_50d_high: Optional[float] = None

    relative_volume: Optional[float] = None
    volume_vs_avg20: Optional[float] = None

    return_3m_pct: Optional[float] = None
    spy_return_3m_pct: Optional[float] = None
    rs_vs_spy_pct: Optional[float] = None
    rs_percentile: Optional[float] = None

    score: ScoreBreakdown
    rating: str
    rating_emoji: str

    mode: str


class ScanResponse(BaseModel):
    mode: str
    universe_size: int
    eligible_count: int
    scanned_count: int
    results: list[ScanResult]
    spy_return_3m_pct: Optional[float] = None
    errors: list[str] = []

    # Symbols served from cache older than its TTL because the upstream fetch
    # failed, and symbols with no usable data at all. Non-zero stale_count means
    # some rows below are not current prices.
    stale_count: int = 0
    failed_count: int = 0
    stale_symbols: list[str] = []


class StockDetail(ScanResult):
    dates: list[str]
    close: list[float]
    sma20_series: list[Optional[float]]
    sma50_series: list[Optional[float]]
    sma200_series: list[Optional[float]]
    volume: list[float]
