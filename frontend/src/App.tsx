import { useEffect, useState } from "react";
import { TrendingUp, AlertTriangle } from "lucide-react";
import type { ModeInfo, ScanResponse } from "./types";
import { fetchModes, fetchScan } from "./api/client";
import { ModeTabs } from "./components/ModeTabs";
import { FilterBar } from "./components/FilterBar";
import { StatBar } from "./components/StatBar";
import { ResultsTable } from "./components/ResultsTable";
import { StockDrawer } from "./components/StockDrawer";

const LEGEND = [
  { emoji: "🔥", rating: "Strong Bullish", range: "10–13 pts", color: "text-emerald-400" },
  { emoji: "🟢", rating: "Bullish", range: "8–9 pts", color: "text-green-400" },
  { emoji: "🟡", rating: "Watchlist", range: "6–7 pts", color: "text-amber-400" },
  { emoji: "⚪", rating: "Ignore", range: "<6 pts", color: "text-zinc-500" },
];

export default function App() {
  const [modes, setModes] = useState<ModeInfo[]>([]);
  const [mode, setMode] = useState("confirmed_breakout");
  const [limit, setLimit] = useState(20);
  const [tickers, setTickers] = useState("");
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetchModes().then(setModes).catch((e) => setError(e.message));
  }, []);

  async function runScan() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchScan(mode, limit, tickers.trim() || undefined);
      setScan(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runScan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
            <TrendingUp size={22} />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">Bullish Breakout Scanner</h1>
            <p className="text-sm text-zinc-500">US equities · trend, momentum, breakout & relative-strength scoring</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-3 text-xs">
          {LEGEND.map((l) => (
            <div key={l.rating} className="flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-2.5 py-1">
              <span>{l.emoji}</span>
              <span className={l.color}>{l.rating}</span>
              <span className="text-zinc-600">{l.range}</span>
            </div>
          ))}
        </div>
      </header>

      <div className="mb-6">
        <ModeTabs modes={modes} active={mode} onChange={setMode} />
      </div>

      <div className="mb-6">
        <FilterBar
          limit={limit}
          onLimitChange={setLimit}
          tickers={tickers}
          onTickersChange={setTickers}
          onRefresh={runScan}
          loading={loading}
        />
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-400">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      <div className="mb-6">
        <StatBar scan={scan} />
      </div>

      <ResultsTable results={scan?.results ?? []} onSelect={setSelected} />

      <footer className="mt-8 text-center text-xs text-zinc-600">
        Universe: market cap &gt; $1B, avg volume &gt; 500K. Ranked by bullish score, not pass/fail filters. Data via Yahoo Finance — for research only, not investment advice.
      </footer>

      {selected && <StockDrawer symbol={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
