import type { ScanResponse } from "../types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5">
      <span className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="font-mono-num text-lg font-semibold text-zinc-100">{value}</span>
    </div>
  );
}

export function StatBar({ scan }: { scan: ScanResponse | null }) {
  if (!scan) return null;
  const spy = scan.spy_return_3m_pct;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      <Stat label="Universe" value={String(scan.universe_size)} />
      <Stat label="Eligible" value={String(scan.eligible_count)} />
      <Stat label="Scanned" value={String(scan.scanned_count)} />
      <Stat label="Matches" value={String(scan.results.length)} />
      <Stat
        label="SPY 3M Return"
        value={spy !== null && spy !== undefined ? `${spy >= 0 ? "+" : ""}${spy.toFixed(2)}%` : "—"}
      />
    </div>
  );
}
