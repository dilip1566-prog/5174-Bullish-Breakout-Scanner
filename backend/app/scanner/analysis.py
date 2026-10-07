from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from app.scanner import indicators as ind
from app.scanner.scoring import compute_score, rating_for_score
from app.models import ScanResult

CONSOLIDATION_WINDOW = 15  # within the 10-20 day range the spec calls for
SMA50_RISING_LOOKBACK = 10
MIN_BARS_REQUIRED = 210  # ~200 SMA + buffer


@dataclass
class RawAnalysis:
    symbol: str
    ok: bool
    reason: Optional[str] = None
    price: Optional[float] = None
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
    df: Optional[pd.DataFrame] = field(default=None, repr=False)


def _finite(x) -> Optional[float]:
    if x is None:
        return None
    try:
        if pd.isna(x) or not np.isfinite(x):
            return None
    except TypeError:
        return None
    return float(x)


def analyze_history(symbol: str, df: pd.DataFrame) -> RawAnalysis:
    if df is None or len(df) < MIN_BARS_REQUIRED:
        return RawAnalysis(symbol=symbol, ok=False, reason="insufficient_history")

    close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]

    sma20_s = ind.sma(close, 20)
    sma50_s = ind.sma(close, 50)
    sma200_s = ind.sma(close, 200)
    rsi_s = ind.rsi(close, 14)
    adx_s, plus_di_s, minus_di_s = ind.adx(high, low, close, 14)
    high20_s = ind.rolling_high(high, 20)
    high50_s = ind.rolling_high(high, 50)

    price = close.iloc[-1]
    sma20 = sma20_s.iloc[-1]
    sma50 = sma50_s.iloc[-1]
    sma200 = sma200_s.iloc[-1]

    sma50_rising = None
    if len(sma50_s.dropna()) > SMA50_RISING_LOOKBACK:
        prev = sma50_s.iloc[-1 - SMA50_RISING_LOOKBACK]
        if pd.notna(prev) and pd.notna(sma50):
            sma50_rising = bool(sma50 > prev)

    rsi14 = rsi_s.iloc[-1]
    adx14 = adx_s.iloc[-1]
    plus_di = plus_di_s.iloc[-1]
    minus_di = minus_di_s.iloc[-1]

    consolidation_pct = ind.consolidation_range_pct(high, low, CONSOLIDATION_WINDOW)

    # Breakout: today's close vs the highest high of the prior window (excluding today)
    prior_high20 = high.iloc[-21:-1].max() if len(high) > 21 else np.nan
    breakout_pct = None
    if pd.notna(prior_high20) and prior_high20 > 0:
        breakout_pct = (price - prior_high20) / prior_high20 * 100

    high20 = high20_s.iloc[-1]
    high50 = high50_s.iloc[-1]
    pct_from_20d_high = ((high20 - price) / high20 * 100) if pd.notna(high20) and high20 > 0 else None
    pct_from_50d_high = ((high50 - price) / high50 * 100) if pd.notna(high50) and high50 > 0 else None

    rvol = ind.relative_volume(volume, 20)
    avg_vol20 = volume.iloc[-21:-1].mean() if len(volume) > 21 else np.nan
    vol_vs_avg20 = (volume.iloc[-1] / avg_vol20) if pd.notna(avg_vol20) and avg_vol20 > 0 else None

    return_3m = ind.pct_return(close, 63)

    return RawAnalysis(
        symbol=symbol,
        ok=True,
        price=_finite(price),
        sma20=_finite(sma20),
        sma50=_finite(sma50),
        sma200=_finite(sma200),
        sma50_rising=sma50_rising,
        rsi14=_finite(rsi14),
        adx14=_finite(adx14),
        plus_di=_finite(plus_di),
        minus_di=_finite(minus_di),
        consolidation_days=CONSOLIDATION_WINDOW,
        consolidation_range_pct=_finite(consolidation_pct),
        breakout_pct=_finite(breakout_pct),
        pct_from_20d_high=_finite(pct_from_20d_high),
        pct_from_50d_high=_finite(pct_from_50d_high),
        relative_volume=_finite(rvol),
        volume_vs_avg20=_finite(vol_vs_avg20),
        return_3m_pct=_finite(return_3m),
        df=df,
    )


def build_scan_result(
    raw: RawAnalysis,
    name: str,
    sector: str,
    market_cap: Optional[float],
    avg_volume: Optional[float],
    spy_return_3m_pct: Optional[float],
    mode: str,
) -> ScanResult:
    score = compute_score(
        price=raw.price,
        sma20=raw.sma20,
        sma50=raw.sma50,
        sma200=raw.sma200,
        sma50_rising=raw.sma50_rising,
        rsi14=raw.rsi14,
        adx14=raw.adx14,
        plus_di=raw.plus_di,
        minus_di=raw.minus_di,
        relative_volume=raw.relative_volume,
        breakout_pct=raw.breakout_pct,
        pct_from_20d_high=raw.pct_from_20d_high,
        pct_from_50d_high=raw.pct_from_50d_high,
        return_3m_pct=raw.return_3m_pct,
        spy_return_3m_pct=spy_return_3m_pct,
    )
    rating, emoji = rating_for_score(score.total)

    rs_vs_spy_pct = None
    if raw.return_3m_pct is not None and spy_return_3m_pct is not None:
        rs_vs_spy_pct = raw.return_3m_pct - spy_return_3m_pct

    return ScanResult(
        symbol=raw.symbol,
        name=name,
        sector=sector,
        price=raw.price,
        market_cap=market_cap,
        avg_volume=avg_volume,
        sma20=raw.sma20,
        sma50=raw.sma50,
        sma200=raw.sma200,
        sma50_rising=raw.sma50_rising,
        rsi14=raw.rsi14,
        adx14=raw.adx14,
        plus_di=raw.plus_di,
        minus_di=raw.minus_di,
        consolidation_days=raw.consolidation_days,
        consolidation_range_pct=raw.consolidation_range_pct,
        breakout_pct=raw.breakout_pct,
        pct_from_20d_high=raw.pct_from_20d_high,
        pct_from_50d_high=raw.pct_from_50d_high,
        relative_volume=raw.relative_volume,
        volume_vs_avg20=raw.volume_vs_avg20,
        return_3m_pct=raw.return_3m_pct,
        spy_return_3m_pct=spy_return_3m_pct,
        rs_vs_spy_pct=rs_vs_spy_pct,
        rs_percentile=None,
        score=score,
        rating=rating,
        rating_emoji=emoji,
        mode=mode,
    )
