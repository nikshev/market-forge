// @trace: REQ-WP-009
//
// The wire shapes of PRD section 28, mirrored. Prices arrive as strings --
// the API sends Decimals that way on purpose, because a price round-tripped
// through a JSON float is a different price.

export const AS_SEEN_THEN = "AS-SEEN-THEN";
export const CURRENT_REFIT = "CURRENT REFIT";
export type ChannelMode = typeof AS_SEEN_THEN | typeof CURRENT_REFIT;

export interface BarOut {
  open_time_ns: number;
  close_time_ns: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume_base: string;
  is_final: boolean;
}

export interface ChannelOut {
  as_of_ns: number;
  model_name: string;
  model_version: string;
  lookback: number;
  center_now: number;
  upper_now: number;
  lower_now: number;
  slope_normalized: number;
  width_pct: number;
  quality_score: number;
  source_max_event_time_ns: number;
  mode: ChannelMode;
}

export interface SignalOut {
  signal_id: string;
  venue: string;
  symbol: string;
  timeframe_ns: number;
  direction: "long" | "short";
  boundary: "upper" | "lower" | "middle";
  state: string;
  opened_at_ns: number;
}

// PRD section 13.11 calls these research defaults, not proven parameters. They
// are the same numbers SignalMachine uses; the chart draws what the engine
// decides on, so a divergence here would draw zones no setup was judged
// against.
export const ZONES = {
  upper: [0.88, 1.0],
  middle: [0.44, 0.56],
  lower: [0.0, 0.12],
} as const;

// PRD section 22.1's six groups, in the PRD's own order and by its own names.
// REQ-US-004 asks to see channel, OFI, volume profile, derivatives and DeFi;
// these are those five plus rejection quality, which section 22.1 scores too.
export const GROUPS = [
  "channel_structure",
  "rejection_quality",
  "order_flow_confirmation",
  "volume_confirmation",
  "derivatives_context",
  "defi_crossvenue_context",
] as const;
export type Group = (typeof GROUPS)[number];

export interface FactorOut {
  group: Group;
  value: number;
  cap: number;
  share: number;
  names: string[];
}

export interface ExplanationOut {
  top_positive: FactorOut[];
  top_negative: FactorOut[];
  missing: Group[];
  feature_snapshot: Record<string, number>;
  model_version: string;
  factors: FactorOut[];
}
