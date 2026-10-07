# Bullish Breakout Scanner

A US-equity swing-trading scanner built around a **weighted bullish score**
instead of pass/fail filters, split into three modes so you're not forcing
every trend-quality stock to also be a fresh breakout.

- **Backend:** Python + FastAPI, data via `yfinance`, pandas/numpy for
  indicator math, disk-cached price history so repeat scans are fast.
- **Frontend:** React + TypeScript + Vite + Tailwind CSS. Sortable results
  table, mode tabs, and a stock drill-down with a price/SMA chart and full
  score checklist.

## Why a score instead of hard filters

Requiring every trend/momentum/breakout/volume/RS condition to pass at once
leaves you with 1-2 stocks on most days. Instead, each condition below is
worth points; results are ranked by total score and you see the top N:

| Condition | Points |
|---|---|
| Price > 20 SMA | +1 |
| Price > 50 SMA | +1 |
| Price > 200 SMA | +1 |
| 20 SMA > 50 SMA | +1 |
| 50 SMA > 200 SMA | +1 |
| RSI(14) 55–75 | +1 |
| ADX(14) > 20 | +1 |
| +DI > -DI | +1 |
| Relative Volume > 1.0x | +1 |
| Breakout > 0.5% | +1 |
| Within 5% of 20/50-day high | +1 |
| 3-month return > SPY | +2 |
| **Max** | **13** |

Rating buckets: `10-13` 🔥 Strong Bullish · `8-9` 🟢 Bullish · `6-7` 🟡 Watchlist · `<6` ⚪ Ignore.

## The three modes

Each mode hard-gates only on the few conditions that define its character;
everything else feeds the score, and results are ranked by score within the
mode.

- **🚀 Early Breakout** — price just reclaimed the 20 SMA, still inside a
  tight (<20%) consolidation, near its 20-day high. More candidates, higher risk.
- **🔥 Confirmed Breakout** — breakout > 0.5% off the prior 20-day high,
  within 5% of the 20/50-day high, relative volume ≥ 0.8x, price above 20 SMA.
  Fewer, higher-quality candidates. This is the main screen.
- **💎 Strong Bullish Trend** — full 20>50>200 SMA stack, price above 200
  SMA, RSI 50-80, ADX ≥ 15. Doesn't need to be breaking out today.

Universe eligibility (applied before any of the above): market cap > $1B,
3-month average volume > 500K.

## Project layout

```
backend/
  app/
    main.py            FastAPI app + CORS
    config.py           thresholds, cache TTLs, paths
    models.py            Pydantic response models
    routers/scan.py     /api/modes, /api/scan, /api/stock/{symbol}
    scanner/
      universe.py       ticker universe loader
      data.py           yfinance fetch + on-disk cache
      indicators.py     SMA/RSI/ADX/+DI-DI/consolidation/RVOL/returns
      scoring.py        13-point score + rating buckets
      analysis.py       per-symbol indicator computation
      modes.py          per-mode gating logic
      service.py        orchestrates a scan end-to-end
    data/universe.csv    default ~230-ticker liquid large-cap universe
  export_scan.py       render a scan to a standalone HTML page
  Dockerfile           API image
  requirements.txt
docker-compose.yml     backend + frontend, restart: unless-stopped
frontend/
  Dockerfile           build + nginx image
  nginx.conf           SPA serve on :5174
  src/
    api/client.ts        fetch wrappers
    components/          ModeTabs, FilterBar, StatBar, ResultsTable, ScoreBadge, StockDrawer
    App.tsx
```

## Running it

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (pinned to `http://localhost:5174`). The frontend
talks to `http://127.0.0.1:8000` by default — override via `VITE_API_BASE`
in `frontend/.env` if you run the backend elsewhere.

## Exporting a scan as a page

`backend/export_scan.py` runs every mode and writes one self-contained HTML
file -- no server, no browser. It calls the scanner directly, so the API does
not need to be running; it reuses the same `backend/.cache/` price history.

```bash
cd backend
.venv/Scripts/python.exe export_scan.py
```

Output lands in `backend/exports/scan.html` (gitignored). Useful flags:

| Flag | Effect |
|---|---|
| `--limit 50` | rows per mode (default 20) |
| `--tickers AAPL,MSFT` | scan an ad-hoc list instead of the universe |
| `--out reports/today.html` | write somewhere else |

The page inlines its own CSS, renders in light and dark, and shows the full
13-point checklist per row, so it can be shared or published as-is.

Rows whose relative volume exceeds 10x or whose breakout exceeds 25% are
marked **check data** and tinted: those values are almost always a corporate
action or a bad vendor bar rather than a tradeable move. The scanner still
scores them, so the flag exists to stop a broken bar quietly ranking near the
top. Thresholds are `RVOL_SUSPECT` and `BREAKOUT_SUSPECT` at the top of the
script.

## Running it with Docker

The compose stack is the way to keep the scanner up without leaving a terminal
open -- both services use `restart: unless-stopped`, so they survive reboots.

```bash
docker compose up -d --build
```

Open `http://localhost:5174`. The API is published on `http://localhost:8000`.

```bash
docker compose logs -f     # follow output
docker compose down        # stop
```

Run an export inside the container; it lands in `backend/exports/` on the host:

```bash
docker compose exec backend python export_scan.py
```

Notes worth knowing:

- **The API base is baked in at build time.** Vite inlines `VITE_API_BASE`, so
  it cannot be changed on a running container. It must be an address the *host
  browser* can reach (`http://127.0.0.1:8000`), not `http://backend:8000` --
  the browser is not on the compose network. To point elsewhere, rebuild:
  `VITE_API_BASE=http://host:9000 docker compose up -d --build`.
- **The price cache is a named volume** (`scanner-cache`), so a cold scan of 235
  symbols happens once rather than on every restart. `docker compose down -v`
  deletes it and forces a full refetch.
- The frontend is served by nginx on port 5174 -- same URL as the dev server, so
  nothing else changes. It listens on both IPv4 and IPv6 loopback.
- `npm run dev` / `uvicorn` still work unchanged for local development; Docker is
  an alternative, not a replacement.

## Customizing the universe

`backend/app/data/universe.csv` ships with ~230 liquid large/mega-cap US
tickers across sectors — a reasonable default pool, not the full market.
To scan the entire NYSE/NASDAQ, replace this file with a full symbol list
(e.g. an exported NASDAQ screener CSV with a `Symbol` column; `Name`/`Sector`
are optional) and point `UNIVERSE_CSV_PATH` at it, or set the env var:

```bash
export UNIVERSE_CSV_PATH=/path/to/full_universe.csv
```

You can also scan an ad-hoc list without touching the universe file at all —
type comma-separated tickers into the search box in the UI, or hit the API
directly: `GET /api/scan?mode=confirmed_breakout&tickers=AAPL,MSFT,NVDA`.

Note: scanning thousands of tickers against Yahoo Finance will be slow on a
cold cache (each symbol is a separate history + info request, parallelized
across 8 workers). Subsequent scans reuse the on-disk cache in
`backend/.cache/` (price history: 4h TTL, info: 24h TTL).

## Disclaimer

For research/educational use only — not investment advice.
