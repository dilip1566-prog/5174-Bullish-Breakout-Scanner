import logging
from typing import Optional

from app.config import MIN_MARKET_CAP, MIN_AVG_VOLUME, BENCHMARK_TICKER
from app.scanner import data as data_mod
from app.scanner.analysis import analyze_history, build_scan_result, RawAnalysis
from app.scanner.modes import passes_mode_gate, MIN_SCORE_BY_MODE, ALL_MODES
from app.scanner.universe import load_universe, parse_custom_tickers, UniverseEntry
from app.models import ScanResponse, ScanResult, StockDetail
from app.scanner import indicators as ind

logger = logging.getLogger("scanner.service")


def run_scan(mode: str, limit: int = 20, custom_tickers: Optional[str] = None) -> ScanResponse:
    entries: list[UniverseEntry] = parse_custom_tickers(custom_tickers) if custom_tickers else load_universe()
    universe_size = len(entries)
    errors: list[str] = []

    symbols = [e.symbol for e in entries]

    data_mod.reset_fetch_stats()

    spy_df = data_mod.get_price_history(BENCHMARK_TICKER)
    spy_raw = analyze_history(BENCHMARK_TICKER, spy_df) if spy_df is not None else RawAnalysis(BENCHMARK_TICKER, ok=False)
    spy_return_3m = spy_raw.return_3m_pct if spy_raw.ok else None

    price_data = data_mod.batch_fetch(symbols)
    info_data = data_mod.batch_fetch_info(symbols)

    eligible_entries = []
    for e in entries:
        info = info_data.get(e.symbol, {})
        market_cap = info.get("market_cap")
        avg_volume = info.get("three_month_average_volume")
        if market_cap is not None and market_cap < MIN_MARKET_CAP:
            continue
        if avg_volume is not None and avg_volume < MIN_AVG_VOLUME:
            continue
        eligible_entries.append((e, market_cap, avg_volume))

    eligible_count = len(eligible_entries)
    scanned_count = 0
    candidates: list[ScanResult] = []

    for entry, market_cap, avg_volume in eligible_entries:
        df = price_data.get(entry.symbol)
        if df is None:
            continue
        scanned_count += 1
        raw = analyze_history(entry.symbol, df)
        if not raw.ok:
            continue
        if not passes_mode_gate(mode, raw):
            continue
        result = build_scan_result(
            raw=raw,
            name=entry.name,
            sector=entry.sector,
            market_cap=market_cap,
            avg_volume=avg_volume,
            spy_return_3m_pct=spy_return_3m,
            mode=mode,
        )
        if result.score.total < MIN_SCORE_BY_MODE[mode]:
            continue
        candidates.append(result)

    # RS percentile among today's candidate pool for this mode
    returns = sorted(
        [c.return_3m_pct for c in candidates if c.return_3m_pct is not None]
    )
    if returns:
        for c in candidates:
            if c.return_3m_pct is None:
                continue
            rank = sum(1 for r in returns if r <= c.return_3m_pct)
            c.rs_percentile = round(rank / len(returns) * 100, 1)

    candidates.sort(key=lambda c: (c.score.total, c.return_3m_pct or -999), reverse=True)
    top = candidates[:limit]

    stats = data_mod.get_fetch_stats()
    if stats["stale"]:
        errors.append(
            "{} symbol(s) served from cache older than its TTL because the upstream "
            "fetch failed -- those prices are not current.".format(len(stats["stale"]))
        )
        logger.warning("Stale data for %d symbol(s): %s",
                       len(stats["stale"]), ", ".join(stats["stale"][:20]))
    if stats["failed"]:
        errors.append("{} symbol(s) had no usable data.".format(len(stats["failed"])))

    return ScanResponse(
        mode=mode,
        universe_size=universe_size,
        eligible_count=eligible_count,
        scanned_count=scanned_count,
        results=top,
        spy_return_3m_pct=spy_return_3m,
        errors=errors,
        stale_count=len(stats["stale"]),
        failed_count=len(stats["failed"]),
        stale_symbols=stats["stale"],
    )


def validate_mode(mode: str) -> None:
    if mode not in ALL_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of {ALL_MODES}")


def get_stock_detail(symbol: str, name: Optional[str] = None, sector: Optional[str] = None) -> Optional[StockDetail]:
    symbol = symbol.upper()
    df = data_mod.get_price_history(symbol)
    if df is None or df.empty:
        return None

    raw = analyze_history(symbol, df)
    if not raw.ok:
        return None

    info = data_mod.get_fast_info(symbol)
    market_cap = info.get("market_cap")
    avg_volume = info.get("three_month_average_volume")

    data_mod.reset_fetch_stats()

    spy_df = data_mod.get_price_history(BENCHMARK_TICKER)
    spy_raw = analyze_history(BENCHMARK_TICKER, spy_df) if spy_df is not None else RawAnalysis(BENCHMARK_TICKER, ok=False)
    spy_return_3m = spy_raw.return_3m_pct if spy_raw.ok else None

    result = build_scan_result(
        raw=raw,
        name=name or symbol,
        sector=sector or "",
        market_cap=market_cap,
        avg_volume=avg_volume,
        spy_return_3m_pct=spy_return_3m,
        mode="detail",
    )

    tail = df.tail(260)
    sma20_series = ind.sma(df["Close"], 20).tail(260)
    sma50_series = ind.sma(df["Close"], 50).tail(260)
    sma200_series = ind.sma(df["Close"], 200).tail(260)

    def series_to_list(s):
        return [None if v is None or v != v else round(float(v), 4) for v in s]

    return StockDetail(
        **result.model_dump(),
        dates=[d.strftime("%Y-%m-%d") for d in tail.index],
        close=series_to_list(tail["Close"]),
        sma20_series=series_to_list(sma20_series),
        sma50_series=series_to_list(sma50_series),
        sma200_series=series_to_list(sma200_series),
        volume=series_to_list(tail["Volume"]),
    )
