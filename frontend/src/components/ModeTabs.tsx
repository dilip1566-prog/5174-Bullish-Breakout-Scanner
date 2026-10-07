import type { ModeInfo } from "../types";

export function ModeTabs({
  modes,
  active,
  onChange,
}: {
  modes: ModeInfo[];
  active: string;
  onChange: (mode: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
      {modes.map((m) => {
        const isActive = m.id === active;
        return (
          <button
            key={m.id}
            onClick={() => onChange(m.id)}
            className={`flex-1 rounded-xl border px-4 py-3 text-left transition-colors ${
              isActive
                ? "border-indigo-500/50 bg-indigo-500/10"
                : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 hover:bg-zinc-900"
            }`}
          >
            <div className={`text-sm font-semibold ${isActive ? "text-indigo-300" : "text-zinc-200"}`}>
              {m.label}
            </div>
            <div className="mt-1 text-xs leading-snug text-zinc-500">{m.description}</div>
          </button>
        );
      })}
    </div>
  );
}
