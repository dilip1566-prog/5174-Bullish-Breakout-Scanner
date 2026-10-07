import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import yfinance as yf

from app.config import CACHE_DIR, HISTORY_PERIOD, HISTORY_INTERVAL, PRICE_CACHE_TTL, INFO_CACHE_TTL, MAX_WORKERS

logger = logging.getLogger("scanner.data")

PRICE_CACHE_DIR = CACHE_DIR / "prices"
INFO_CACHE_DIR = CACHE_DIR / "info"
PRICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
INFO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# A failed upstream fetch falls back to whatever is on disk, even when that copy
# has outlived its TTL. That is the right call -- stale numbers beat no numbers --
# but the caller has to be able to tell, otherwise a scan reports day-old prices
# as if they were current. These counters make the fallback visible.
_stats_lock = threading.Lock()
_stale_symbols: set[str] = set()
_failed_symbols: set[str] = set()


def reset_fetch_stats() -> None:
    with _stats_lock:
        _stale_symbols.clear()
        _failed_symbols.clear()


def get_fetch_stats() -> dict:
    with _stats_lock:
        return {
            "stale": sorted(_stale_symbols),
            "failed": sorted(_failed_symbols),
        }


def _mark_stale(symbol: str) -> None:
    with _stats_lock:
        _stale_symbols.add(symbol.upper())


def _mark_failed(symbol: str) -> None:
    with _stats_lock:
        _failed_symbols.add(symbol.upper())


def _price_cache_path(symbol: str) -> "pd.io.common.Path":
    return PRICE_CACHE_DIR / f"{symbol.upper()}.parquet"


def _info_cache_path(symbol: str) -> "pd.io.common.Path":
    return INFO_CACHE_DIR / f"{symbol.upper()}.json"


def get_price_history(symbol: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """Fetch OHLCV history for a symbol, using an on-disk cache to avoid
    re-hitting yfinance on every scan."""
    path = _price_cache_path(symbol)
    if not force_refresh and path.exists():
        age = time.time() - path.stat().st_mtime
        if age < PRICE_CACHE_TTL:
            try:
                return pd.read_parquet(path)
            except Exception:
                pass

    try:
        df = yf.Ticker(symbol).history(period=HISTORY_PERIOD, interval=HISTORY_INTERVAL, auto_adjust=True)
    except Exception as e:
        logger.warning("Failed to fetch history for %s: %s", symbol, e)
        df = None

    if df is None or df.empty:
        # Upstream gave us nothing. Serve the cached copy if there is one, but
        # record that this symbol's numbers are older than the TTL allows.
        if path.exists():
            try:
                cached = pd.read_parquet(path)
                _mark_stale(symbol)
                return cached
            except Exception:
                _mark_failed(symbol)
                return None
        _mark_failed(symbol)
        return None

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    try:
        df.to_parquet(path)
    except Exception as e:
        logger.warning("Failed to cache history for %s: %s", symbol, e)
    return df


def get_fast_info(symbol: str, force_refresh: bool = False) -> dict:
    """Fetch lightweight info (market cap, avg volume) with disk caching."""
    path = _info_cache_path(symbol)
    if not force_refresh and path.exists():
        age = time.time() - path.stat().st_mtime
        if age < INFO_CACHE_TTL:
            try:
                return json.loads(path.read_text())
            except Exception:
                pass

    info = {}
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        info = {
            "market_cap": getattr(fi, "market_cap", None),
            "last_price": getattr(fi, "last_price", None),
            "three_month_average_volume": getattr(fi, "three_month_average_volume", None),
        }
    except Exception as e:
        logger.warning("Failed to fetch fast_info for %s: %s", symbol, e)

    if info and info.get("market_cap") is not None:
        try:
            path.write_text(json.dumps(info))
        except Exception:
            pass
    elif path.exists():
        try:
            cached = json.loads(path.read_text())
            _mark_stale(symbol)
            return cached
        except Exception:
            return info
    return info


def batch_fetch(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Fetch price history for many symbols in parallel."""
    results: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(get_price_history, s): s for s in symbols}
        for fut in as_completed(futures):
            symbol = futures[fut]
            try:
                df = fut.result()
                if df is not None and not df.empty:
                    results[symbol] = df
            except Exception as e:
                logger.warning("Batch fetch failed for %s: %s", symbol, e)
    return results


def batch_fetch_info(symbols: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(get_fast_info, s): s for s in symbols}
        for fut in as_completed(futures):
            symbol = futures[fut]
            try:
                info = fut.result()
                if info:
                    results[symbol] = info
            except Exception as e:
                logger.warning("Batch info fetch failed for %s: %s", symbol, e)
    return results
