import logging

from fastapi import APIRouter, HTTPException, Query

from app.models import ScanResponse, StockDetail
from app.scanner import service
from app.scanner.modes import ALL_MODES, MODE_LABELS, MODE_DESCRIPTIONS
from app.scanner.universe import load_universe

logger = logging.getLogger("routers.scan")

router = APIRouter(prefix="/api", tags=["scan"])


@router.get("/modes")
def get_modes():
    return [
        {"id": m, "label": MODE_LABELS[m], "description": MODE_DESCRIPTIONS[m]}
        for m in ALL_MODES
    ]


@router.get("/universe")
def get_universe():
    entries = load_universe()
    return {"count": len(entries), "symbols": [e.symbol for e in entries]}


@router.get("/scan", response_model=ScanResponse)
def scan(
    mode: str = Query("confirmed_breakout"),
    limit: int = Query(20, ge=1, le=100),
    tickers: str | None = Query(None, description="Comma separated custom ticker list to scan instead of the default universe"),
):
    try:
        service.validate_mode(mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return service.run_scan(mode=mode, limit=limit, custom_tickers=tickers)
    except Exception as e:
        logger.exception("Scan failed")
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}")


@router.get("/stock/{symbol}", response_model=StockDetail)
def stock_detail(symbol: str):
    detail = service.get_stock_detail(symbol)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
    return detail
