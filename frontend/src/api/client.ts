import type { ScanResponse, StockDetail, ModeInfo } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export function fetchModes(): Promise<ModeInfo[]> {
  return getJson<ModeInfo[]>("/api/modes");
}

export function fetchScan(mode: string, limit: number, tickers?: string): Promise<ScanResponse> {
  const params = new URLSearchParams({ mode, limit: String(limit) });
  if (tickers) params.set("tickers", tickers);
  return getJson<ScanResponse>(`/api/scan?${params.toString()}`);
}

export function fetchStockDetail(symbol: string): Promise<StockDetail> {
  return getJson<StockDetail>(`/api/stock/${encodeURIComponent(symbol)}`);
}
