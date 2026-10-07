"""Technical indicator calculations used by the scanner.

All functions take/return pandas Series aligned to the input OHLCV DataFrame.
Wilder's smoothing (as used by classic RSI/ADX) is implemented via an EMA
with alpha = 1/window, which matches the standard definitions.
"""
import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    rsi_val = rsi_val.where(avg_loss != 0, 100)
    return rsi_val


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (adx, plus_di, minus_di) using Wilder smoothing."""
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    tr = true_range(high, low, close)
    atr = tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    plus_di = 100 * (plus_dm.ewm(alpha=1 / window, min_periods=window, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / window, min_periods=window, adjust=False).mean() / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    return adx_val, plus_di, minus_di


def rolling_high(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).max()


def rolling_low(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).min()


def consolidation_range_pct(high: pd.Series, low: pd.Series, window: int) -> float:
    """Percent range (high-low)/low over the trailing `window` days."""
    recent_high = high.iloc[-window:].max()
    recent_low = low.iloc[-window:].min()
    if recent_low <= 0:
        return np.nan
    return (recent_high - recent_low) / recent_low * 100


def relative_volume(volume: pd.Series, window: int = 20) -> float:
    """Latest volume divided by the average of the prior `window` days
    (excluding the latest bar so a huge breakout day doesn't inflate its
    own baseline)."""
    if len(volume) < window + 1:
        return np.nan
    baseline = volume.iloc[-(window + 1):-1].mean()
    if baseline <= 0:
        return np.nan
    return volume.iloc[-1] / baseline


def pct_return(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        return np.nan
    start = close.iloc[-days - 1]
    end = close.iloc[-1]
    if start <= 0:
        return np.nan
    return (end / start - 1) * 100
