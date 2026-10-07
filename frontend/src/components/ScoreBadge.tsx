const RATING_STYLES: Record<string, string> = {
  "Strong Bullish": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Bullish: "bg-green-500/15 text-green-400 border-green-500/30",
  Watchlist: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  Ignore: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
};

export function ScoreBadge({ rating, emoji }: { rating: string; emoji: string }) {
  const style = RATING_STYLES[rating] ?? RATING_STYLES.Ignore;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap ${style}`}>
      <span>{emoji}</span>
      <span>{rating}</span>
    </span>
  );
}

export function ScoreBar({ total, max = 13 }: { total: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (total / max) * 100));
  let color = "bg-zinc-500";
  if (total >= 10) color = "bg-emerald-500";
  else if (total >= 8) color = "bg-green-500";
  else if (total >= 6) color = "bg-amber-500";

  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="h-1.5 flex-1 rounded-full bg-zinc-800 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono-num text-xs text-zinc-300 w-10 text-right">{total}/{max}</span>
    </div>
  );
}
