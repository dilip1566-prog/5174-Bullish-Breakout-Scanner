import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Check, Loader2, X, XIcon } from "lucide-react";
import type { StockDetail } from "../types";
import { fetchStockDetail } from "../api/client";
import { ScoreBadge, ScoreBar } from "./ScoreBadge";

const CHECKLIST: { key: keyof StockDetail["score"]; label: string; points: number }[] = [
  { key: "price_gt_sma20", label: "Price > 20 SMA", points: 1 },
  { key: "price_gt_sma50", label: "Price > 50 SMA", points: 1 },
  { key: "price_gt_sma200", label: "Price > 200 SMA", points: 1 },
  { key: "sma20_gt_sma50", label: "20 SMA > 50 SMA", points: 1 },
  { key: "sma50_gt_sma200", label: "50 SMA > 200 SMA", points: 1 },
  { key: "rsi_in_range", label: "RSI(14) 55–75", points: 1 },
  { key: "adx_strong", label: "ADX(14) > 20", points: 1 },
  { key: "di_bullish", label: "+DI > -DI", points: 1 },
  { key: "rvol_strong", label: "Relative Volume > 1.0x", points: 1 },
  { key: "breakout_confirmed", label: "Breakout > 0.5%", points: 1 },
  { key: "near_high", label: "Within 5% of 20/50-day high", points: 1 },
  { key: "rs_vs_spy", label: "3-Month Return > SPY", points: 2 },
];

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 text-zinc-400">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2" style={{ color: p.color }}>
          <span>{p.name}:</span>
          <span className="font-mono-num">{p.value?.toFixed?.(2) ?? "—"}</span>
        </div>
      ))}
    </div>
  );
}

export function StockDrawer({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setDetail(null);
    setError(null);
    setLoading(true);
    fetchStockDetail(symbol)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  const chartData = detail?.dates.slice(-180).map((d, i) => {
    const offset = detail.dates.length - detail.dates.slice(-180).length;
    return {
      date: d,
      close: detail.close[offset + i],
      sma20: detail.sma20_series[offset + i],
      sma50: detail.sma50_series[offset + i],
      sma200: detail.sma200_series[offset + i],
    };
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onClose}>
      <div
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-zinc-100">{symbol}</h2>
            {detail && <p className="text-sm text-zinc-500">{detail.name} · {detail.sector}</p>}
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200">
            <X size={20} />
          </button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 py-16 justify-center text-zinc-500">
            <Loader2 className="animate-spin" size={18} /> Loading…
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-400">
            <XIcon size={16} /> {error}
          </div>
        )}

        {detail && (
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3">
              <div>
                <div className="font-mono-num text-2xl font-semibold text-zinc-100">${detail.price.toFixed(2)}</div>
                <div className="text-xs text-zinc-500">Last close</div>
              </div>
              <ScoreBadge rating={detail.rating} emoji={detail.rating_emoji} />
            </div>

            <div className="h-64 w-full rounded-xl border border-zinc-800 bg-zinc-900/30 p-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#1f2028" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "#71717a" }}
                    tickFormatter={(v) => v.slice(5)}
                    minTickGap={40}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fontSize: 10, fill: "#71717a" }}
                    width={50}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="close" name="Close" stroke="#e5e7eb" dot={false} strokeWidth={1.75} />
                  <Line type="monotone" dataKey="sma20" name="SMA20" stroke="#60a5fa" dot={false} strokeWidth={1.25} />
                  <Line type="monotone" dataKey="sma50" name="SMA50" stroke="#fbbf24" dot={false} strokeWidth={1.25} />
                  <Line type="monotone" dataKey="sma200" name="SMA200" stroke="#f87171" dot={false} strokeWidth={1.25} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-zinc-300">Bullish Score Breakdown</h3>
                <ScoreBar total={detail.score.total} max={detail.score.max_total} />
              </div>
              <div className="divide-y divide-zinc-900 rounded-xl border border-zinc-800 bg-zinc-900/30">
                {CHECKLIST.map((item) => {
                  const passed = Boolean(detail.score[item.key]);
                  return (
                    <div key={String(item.key)} className="flex items-center justify-between px-4 py-2.5 text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded-full ${
                            passed ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-600"
                          }`}
                        >
                          {passed ? <Check size={13} /> : <X size={13} />}
                        </span>
                        <span className={passed ? "text-zinc-200" : "text-zinc-500"}>{item.label}</span>
                      </div>
                      <span className={`font-mono-num text-xs ${passed ? "text-emerald-400" : "text-zinc-600"}`}>
                        {passed ? `+${item.points}` : "0"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <Metric label="RSI(14)" value={detail.rsi14?.toFixed(1)} />
              <Metric label="ADX(14)" value={detail.adx14?.toFixed(1)} />
              <Metric label="+DI / -DI" value={`${detail.plus_di?.toFixed(1)} / ${detail.minus_di?.toFixed(1)}`} />
              <Metric label="Rel. Volume" value={detail.relative_volume ? `${detail.relative_volume.toFixed(2)}x` : undefined} />
              <Metric label="Breakout %" value={detail.breakout_pct !== null && detail.breakout_pct !== undefined ? `${detail.breakout_pct.toFixed(2)}%` : undefined} />
              <Metric label="Consolidation Range" value={detail.consolidation_range_pct ? `${detail.consolidation_range_pct.toFixed(1)}%` : undefined} />
              <Metric label="% from 20D High" value={detail.pct_from_20d_high !== null && detail.pct_from_20d_high !== undefined ? `${detail.pct_from_20d_high.toFixed(1)}%` : undefined} />
              <Metric label="% from 50D High" value={detail.pct_from_50d_high !== null && detail.pct_from_50d_high !== undefined ? `${detail.pct_from_50d_high.toFixed(1)}%` : undefined} />
              <Metric label="3M Return vs SPY" value={detail.rs_vs_spy_pct !== null && detail.rs_vs_spy_pct !== undefined ? `${detail.rs_vs_spy_pct >= 0 ? "+" : ""}${detail.rs_vs_spy_pct.toFixed(1)}%` : undefined} />
              <Metric label="RS Percentile" value={detail.rs_percentile !== null && detail.rs_percentile !== undefined ? `${detail.rs_percentile.toFixed(0)}th` : undefined} />
              <Metric label="Market Cap" value={detail.market_cap ? `$${(detail.market_cap / 1e9).toFixed(1)}B` : undefined} />
              <Metric label="Avg Volume" value={detail.avg_volume ? `${(detail.avg_volume / 1e6).toFixed(1)}M` : undefined} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</div>
      <div className="font-mono-num text-sm text-zinc-200">{value ?? "—"}</div>
    </div>
  );
}
