import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { ScanResult } from "../types";
import { ScoreBadge, ScoreBar } from "./ScoreBadge";

type SortKey =
  | "score"
  | "symbol"
  | "price"
  | "rsi14"
  | "adx14"
  | "relative_volume"
  | "breakout_pct"
  | "return_3m_pct"
  | "rs_vs_spy_pct";

interface Column {
  key: SortKey;
  label: string;
  align?: "left" | "right";
}

const COLUMNS: Column[] = [
  { key: "symbol", label: "Symbol", align: "left" },
  { key: "price", label: "Price", align: "right" },
  { key: "score", label: "Bullish Score", align: "left" },
  { key: "rsi14", label: "RSI(14)", align: "right" },
  { key: "adx14", label: "ADX(14)", align: "right" },
  { key: "relative_volume", label: "Rel Vol", align: "right" },
  { key: "breakout_pct", label: "Breakout %", align: "right" },
  { key: "return_3m_pct", label: "3M Return", align: "right" },
  { key: "rs_vs_spy_pct", label: "RS vs SPY", align: "right" },
];

function fmt(n: number | null | undefined, digits = 2, suffix = "") {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${n.toFixed(digits)}${suffix}`;
}

function fmtSigned(n: number | null | undefined, digits = 2, suffix = "%") {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}${suffix}`;
}

function getSortValue(r: ScanResult, key: SortKey): number | string {
  switch (key) {
    case "score":
      return r.score.total;
    case "symbol":
      return r.symbol;
    default:
      return (r[key] as number | null | undefined) ?? -Infinity;
  }
}

export function ResultsTable({
  results,
  onSelect,
}: {
  results: ScanResult[];
  onSelect: (symbol: string) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const copy = [...results];
    copy.sort((a, b) => {
      const av = getSortValue(a, sortKey);
      const bv = getSortValue(b, sortKey);
      let cmp: number;
      if (typeof av === "string" || typeof bv === "string") {
        cmp = String(av).localeCompare(String(bv));
      } else {
        cmp = (av as number) - (bv as number);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [results, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (results.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 py-16 text-center text-sm text-zinc-500">
        No matches for this mode yet. Try running a scan, widening the ticker list, or switching modes.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full min-w-[900px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/70 text-left text-xs uppercase tracking-wide text-zinc-500">
            <th className="px-3 py-2.5 font-medium">#</th>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => toggleSort(col.key)}
                className={`cursor-pointer select-none px-3 py-2.5 font-medium hover:text-zinc-300 ${
                  col.align === "right" ? "text-right" : "text-left"
                }`}
              >
                <span className={`inline-flex items-center gap-1 ${col.align === "right" ? "flex-row-reverse" : ""}`}>
                  {col.label}
                  {sortKey === col.key ? (
                    sortDir === "asc" ? (
                      <ArrowUp size={12} />
                    ) : (
                      <ArrowDown size={12} />
                    )
                  ) : (
                    <ArrowUpDown size={12} className="opacity-30" />
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr
              key={r.symbol}
              onClick={() => onSelect(r.symbol)}
              className="cursor-pointer border-b border-zinc-900 transition-colors hover:bg-zinc-900/60"
            >
              <td className="px-3 py-2.5 font-mono-num text-zinc-500">{i + 1}</td>
              <td className="px-3 py-2.5">
                <div className="font-semibold text-zinc-100">{r.symbol}</div>
                <div className="max-w-[160px] truncate text-xs text-zinc-500">{r.name}</div>
              </td>
              <td className="px-3 py-2.5 text-right font-mono-num text-zinc-200">${fmt(r.price)}</td>
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <ScoreBadge rating={r.rating} emoji={r.rating_emoji} />
                  <ScoreBar total={r.score.total} max={r.score.max_total} />
                </div>
              </td>
              <td className="px-3 py-2.5 text-right font-mono-num text-zinc-300">{fmt(r.rsi14, 1)}</td>
              <td className="px-3 py-2.5 text-right font-mono-num text-zinc-300">{fmt(r.adx14, 1)}</td>
              <td className="px-3 py-2.5 text-right font-mono-num text-zinc-300">{fmt(r.relative_volume, 2, "x")}</td>
              <td
                className={`px-3 py-2.5 text-right font-mono-num ${
                  (r.breakout_pct ?? 0) > 0 ? "text-emerald-400" : "text-zinc-400"
                }`}
              >
                {fmtSigned(r.breakout_pct)}
              </td>
              <td
                className={`px-3 py-2.5 text-right font-mono-num ${
                  (r.return_3m_pct ?? 0) > 0 ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {fmtSigned(r.return_3m_pct)}
              </td>
              <td
                className={`px-3 py-2.5 text-right font-mono-num ${
                  (r.rs_vs_spy_pct ?? 0) > 0 ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {fmtSigned(r.rs_vs_spy_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
