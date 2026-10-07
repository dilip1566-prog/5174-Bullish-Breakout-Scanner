from app.models import ScoreBreakdown

RSI_LOW, RSI_HIGH = 55, 75
ADX_MIN = 20
RVOL_MIN = 1.0
BREAKOUT_MIN_PCT = 0.5
NEAR_HIGH_MAX_PCT = 5.0


def compute_score(
    price: float,
    sma20: float | None,
    sma50: float | None,
    sma200: float | None,
    sma50_rising: bool | None,
    rsi14: float | None,
    adx14: float | None,
    plus_di: float | None,
    minus_di: float | None,
    relative_volume: float | None,
    breakout_pct: float | None,
    pct_from_20d_high: float | None,
    pct_from_50d_high: float | None,
    return_3m_pct: float | None,
    spy_return_3m_pct: float | None,
) -> ScoreBreakdown:
    def safe_gt(a, b):
        return a is not None and b is not None and a > b

    price_gt_sma20 = safe_gt(price, sma20)
    price_gt_sma50 = safe_gt(price, sma50)
    price_gt_sma200 = safe_gt(price, sma200)
    sma20_gt_sma50 = safe_gt(sma20, sma50)
    sma50_gt_sma200 = safe_gt(sma50, sma200)

    rsi_in_range = rsi14 is not None and RSI_LOW <= rsi14 <= RSI_HIGH
    adx_strong = adx14 is not None and adx14 > ADX_MIN
    di_bullish = safe_gt(plus_di, minus_di)
    rvol_strong = relative_volume is not None and relative_volume > RVOL_MIN
    breakout_confirmed = breakout_pct is not None and breakout_pct > BREAKOUT_MIN_PCT

    near_high = False
    if pct_from_20d_high is not None and pct_from_20d_high <= NEAR_HIGH_MAX_PCT:
        near_high = True
    if pct_from_50d_high is not None and pct_from_50d_high <= NEAR_HIGH_MAX_PCT:
        near_high = True

    rs_vs_spy = (
        return_3m_pct is not None
        and spy_return_3m_pct is not None
        and return_3m_pct > spy_return_3m_pct
    )

    total = (
        int(price_gt_sma20)
        + int(price_gt_sma50)
        + int(price_gt_sma200)
        + int(sma20_gt_sma50)
        + int(sma50_gt_sma200)
        + int(rsi_in_range)
        + int(adx_strong)
        + int(di_bullish)
        + int(rvol_strong)
        + int(breakout_confirmed)
        + int(near_high)
        + (2 if rs_vs_spy else 0)
    )

    return ScoreBreakdown(
        price_gt_sma20=price_gt_sma20,
        price_gt_sma50=price_gt_sma50,
        price_gt_sma200=price_gt_sma200,
        sma20_gt_sma50=sma20_gt_sma50,
        sma50_gt_sma200=sma50_gt_sma200,
        rsi_in_range=rsi_in_range,
        adx_strong=adx_strong,
        di_bullish=di_bullish,
        rvol_strong=rvol_strong,
        breakout_confirmed=breakout_confirmed,
        near_high=near_high,
        rs_vs_spy=rs_vs_spy,
        total=total,
    )


def rating_for_score(total: int) -> tuple[str, str]:
    if total >= 10:
        return "Strong Bullish", "🔥"
    if total >= 8:
        return "Bullish", "🟢"
    if total >= 6:
        return "Watchlist", "🟡"
    return "Ignore", "⚪"
