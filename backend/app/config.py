import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR.parent / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UNIVERSE_CSV_PATH = Path(os.environ.get("UNIVERSE_CSV_PATH", DATA_DIR / "universe.csv"))

BENCHMARK_TICKER = "SPY"

# Universe eligibility (hard filters)
MIN_MARKET_CAP = 1_000_000_000
MIN_AVG_VOLUME = 500_000

# History window needed for 200 SMA + 3M return + lookbacks, with buffer
HISTORY_PERIOD = "18mo"
HISTORY_INTERVAL = "1d"

# Cache TTL for price history / info (seconds)
PRICE_CACHE_TTL = 60 * 60 * 4  # 4 hours
INFO_CACHE_TTL = 60 * 60 * 24  # 24 hours

# Concurrency for batch downloads
MAX_WORKERS = 8
