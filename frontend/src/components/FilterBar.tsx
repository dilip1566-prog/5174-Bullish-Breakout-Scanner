import { RefreshCw, Search } from "lucide-react";

export function FilterBar({
  limit,
  onLimitChange,
  tickers,
  onTickersChange,
  onRefresh,
  loading,
}: {
  limit: number;
  onLimitChange: (n: number) => void;
  tickers: string;
  onTickersChange: (s: string) => void;
  onRefresh: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-1 items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
        <Search size={15} className="text-zinc-500" />
        <input
          value={tickers}
          onChange={(e) => onTickersChange(e.target.value)}
          placeholder="Optional: scan custom tickers, e.g. AAPL,MSFT,NVDA (leave blank for full universe)"
          className="w-full bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none"
        />
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-zinc-400">
          Top
          <select
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            className="rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1.5 text-zinc-200 outline-none"
          >
            {[10, 20, 30, 50].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          {loading ? "Scanning…" : "Run Scan"}
        </button>
      </div>
    </div>
  );
}
