import csv
from dataclasses import dataclass

from app.config import UNIVERSE_CSV_PATH, BENCHMARK_TICKER


@dataclass
class UniverseEntry:
    symbol: str
    name: str
    sector: str


def load_universe() -> list[UniverseEntry]:
    entries: list[UniverseEntry] = []
    with open(UNIVERSE_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row["Symbol"].strip().upper()
            if symbol == BENCHMARK_TICKER:
                continue
            entries.append(UniverseEntry(symbol=symbol, name=row["Name"].strip(), sector=row["Sector"].strip()))
    return entries


def parse_custom_tickers(raw: str) -> list[UniverseEntry]:
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    return [UniverseEntry(symbol=s, name=s, sector="Custom") for s in symbols]
