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

// PRD section 27.2's toggleable layers, in the PRD's order. Mirrors
// `channelflow.alerting.Overlay`: the alert writes these names into the deep
// link and the chart reads them back, so a divergence would silently drop
// whichever layer got renamed on one side.
export const OVERLAYS = [
  "candles",
  "channel_center",
  "channel_bounds",
  "forecast_corridor",
  "signal_zones",
  "signal_marker",
  "volume_profile",
  "poc_vah_val",
  "vwap",
  "lob_walls",
  "dex_liquidity_bands",
  "liquidation_levels",
] as const;
export type Overlay = (typeof OVERLAYS)[number];

// What the chart shows when the link did not say. The four layers REQ-WP-009's
// acceptance names, plus the profile REQ-WP-012 added -- the state this chart
// had before any link carried overlays.
export const DEFAULT_OVERLAYS: readonly Overlay[] = [
  "candles",
  "channel_center",
  "channel_bounds",
  "signal_zones",
  "signal_marker",
  "volume_profile",
];

/** PRD section 28's feature point: an instant, and a mapping of what was
 * measured then. A feature absent from the mapping is silent rather than
 * zero -- see `panes.ts`, where drawing the difference is the whole job. */
export interface FeaturePointOut {
  at_ns: number;
  values: Record<string, number>;
}

export interface FeatureSeriesResponse {
  points: FeaturePointOut[];
}

/** PRD section 28's confirmed extremum. Both instants travel: `extremum_time_ns`
 * is where the marker goes and `known_at_ns` is the earliest instant it may be
 * drawn at all (REQ-WP-028). */
export interface ConfirmedExtremumOut {
  extremum_id: string;
  extremum_type: string;
  extremum_time_ns: number;
  known_at_ns: number;
  price: string;
  confirmation_lag_bars: number;
  prominence_bps: number | null;
  source_candidate_id: string | null;
}

export interface ExtremumCandidateOut {
  candidate_id: string;
  candidate_type: string;
  candidate_time_ns: number;
  observed_at_ns: number;
  price: string;
  structural_score: number;
}

export interface ExtremaResponse {
  confirmed: ConfirmedExtremumOut[];
  candidates: ExtremumCandidateOut[];
}

// PRD section 44A's position and stop-decision shapes, mirrored (REQ-WP-032).
// Prices are strings for the reason every other price here is: a Decimal round
// -tripped through a JSON float is a different price, and a stop is the one
// number in this system a rounding error would move.

export interface StopAnchorOut {
  kind: string;
  price: string;
  known_at_ns: number;
  description: string;
}

export interface StopProposalOut {
  at_ns: number;
  price: string;
  phase: string;
  reasons: string[];
  // Null means this decision rested on no structural level -- which is what a
  // hold with nothing knowable is. Never the previous anchor.
  anchor: StopAnchorOut | null;
  moved: boolean;
  refused: boolean;
}

export interface PositionOut {
  position_id: string;
  side: "LONG" | "SHORT";
  entry_time_ns: number;
  average_entry_price: string;
  initial_stop_price: string;
  // Null means no catastrophic stop was set. Never the initial stop: those are
  // two different promises, and one line where the position has two is a lie
  // about how much room is left.
  hard_stop_price: string | null;
  current_strategy_stop: string;
}

export interface ExcursionOut {
  mfe_r: number | null;
  mae_r: number | null;
}
