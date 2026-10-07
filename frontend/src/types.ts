export interface ScoreBreakdown {
  price_gt_sma20: boolean;
  price_gt_sma50: boolean;
  price_gt_sma200: boolean;
  sma20_gt_sma50: boolean;
  sma50_gt_sma200: boolean;
  rsi_in_range: boolean;
  adx_strong: boolean;
  di_bullish: boolean;
  rvol_strong: boolean;
  breakout_confirmed: boolean;
  near_high: boolean;
  rs_vs_spy: boolean;
  total: number;
  max_total: number;
}

export interface ScanResult {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  market_cap?: number | null;
  avg_volume?: number | null;

  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  sma50_rising?: boolean | null;

  rsi14?: number | null;
  adx14?: number | null;
  plus_di?: number | null;
  minus_di?: number | null;

  consolidation_days?: number | null;
  consolidation_range_pct?: number | null;
  breakout_pct?: number | null;
  pct_from_20d_high?: number | null;
  pct_from_50d_high?: number | null;

  relative_volume?: number | null;
  volume_vs_avg20?: number | null;

  return_3m_pct?: number | null;
  spy_return_3m_pct?: number | null;
  rs_vs_spy_pct?: number | null;
  rs_percentile?: number | null;

  score: ScoreBreakdown;
  rating: string;
  rating_emoji: string;
  mode: string;
}

export interface ScanResponse {
  mode: string;
  universe_size: number;
  eligible_count: number;
  scanned_count: number;
  results: ScanResult[];
  spy_return_3m_pct?: number | null;
  errors: string[];
}

export interface StockDetail extends ScanResult {
  dates: string[];
  close: number[];
  sma20_series: (number | null)[];
  sma50_series: (number | null)[];
  sma200_series: (number | null)[];
  volume: number[];
}

export interface ModeInfo {
  id: string;
  label: string;
  description: string;
}
