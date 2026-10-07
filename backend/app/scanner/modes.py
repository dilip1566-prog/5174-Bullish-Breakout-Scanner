"""The three scan modes.

Rather than requiring every single criterion to pass (which the user found
produced almost no results), each mode only hard-gates on the handful of
conditions that define *that mode's character*. Everything else feeds into
the 13-point bullish score, and results are ranked by score.
"""
from app.scanner.analysis import RawAnalysis

EARLY_BREAKOUT = "early_breakout"
CONFIRMED_BREAKOUT = "confirmed_breakout"
STRONG_BULLISH_TREND = "strong_bullish_trend"

ALL_MODES = [EARLY_BREAKOUT, CONFIRMED_BREAKOUT, STRONG_BULLISH_TREND]

MODE_LABELS = {
    EARLY_BREAKOUT: "🚀 Early Breakout",
    CONFIRMED_BREAKOUT: "🔥 Confirmed Breakout",
    STRONG_BULLISH_TREND: "💎 Strong Bullish Trend",
}

MODE_DESCRIPTIONS = {
    EARLY_BREAKOUT: "Stocks just beginning to break out of consolidation. More candidates, higher risk.",
    CONFIRMED_BREAKOUT: "Breakout confirmed by volume, trend, and relative strength. Fewer, higher-quality candidates.",
    STRONG_BULLISH_TREND: "Established 20>50>200 uptrend with strong momentum. Doesn't need to be breaking out today.",
}

MIN_SCORE_BY_MODE = {
    EARLY_BREAKOUT: 5,
    CONFIRMED_BREAKOUT: 6,
    STRONG_BULLISH_TREND: 6,
}

CONSOLIDATION_MAX_RANGE_PCT = 20.0


def passes_mode_gate(mode: str, raw: RawAnalysis) -> bool:
    if not raw.ok:
        return False

    if mode == EARLY_BREAKOUT:
        if raw.price is None or raw.sma20 is None or raw.price <= raw.sma20:
            return False
        if raw.consolidation_range_pct is None or raw.consolidation_range_pct >= CONSOLIDATION_MAX_RANGE_PCT:
            return False
        if raw.pct_from_20d_high is None or raw.pct_from_20d_high > 8:
            return False
        return True

    if mode == CONFIRMED_BREAKOUT:
        if raw.breakout_pct is None or raw.breakout_pct <= 0.5:
            return False
        near_high = (raw.pct_from_20d_high is not None and raw.pct_from_20d_high <= 5) or (
            raw.pct_from_50d_high is not None and raw.pct_from_50d_high <= 5
        )
        if not near_high:
            return False
        if raw.relative_volume is None or raw.relative_volume < 0.8:
            return False
        if raw.price is None or raw.sma20 is None or raw.price <= raw.sma20:
            return False
        return True

    if mode == STRONG_BULLISH_TREND:
        if None in (raw.sma20, raw.sma50, raw.sma200, raw.price):
            return False
        if not (raw.sma20 > raw.sma50 > raw.sma200):
            return False
        if raw.price <= raw.sma200:
            return False
        if raw.rsi14 is None or not (50 <= raw.rsi14 <= 80):
            return False
        if raw.adx14 is None or raw.adx14 < 15:
            return False
        return True

    raise ValueError(f"Unknown mode: {mode}")
