// @trace: REQ-WP-027
// @trace: REQ-WP-030
//
// PRD section 27.3's lower panes, for the three Phase 2 has data for.
//
// The decision about what to draw lives here rather than in a component, the
// way `series.ts` does and for the reason it records: lightweight-charts needs
// a laid-out container, jsdom does not provide one, and a component test can
// never see a line. The part that can be wrong is the part that gets tested.
//
// The rule this whole module exists for: **a point carrying no value for the
// selected feature is silent, not zero.** Drawn at zero it becomes a reading --
// a flat line through the middle of a CVD pane says "no net delta", which is a
// claim about the market rather than about the data.

import type { FeaturePointOut } from "./types";

export interface Pane {
  /** The registered feature name, as the API returns it. */
  feature: string;
  /** What a reader picks it by. */
  label: string;
}

// PRD section 27.3 lists nine panes. Eight are here: the order-flow three from
// [[REQ-WP-027]], Phase 3's four added by [[REQ-WP-030]], and Phase 4's swap
// imbalance added by [[REQ-WP-059]] once `dex_swap_imbalance` existed to draw.
//
// **`DEX active liquidity` is still absent, and deliberately.** §18.12.2's
// `active_liquidity` lives on a `LiquidityState` nothing reconstructs, which on
// HyperEVM needs an archive node no public endpoint provides ([[ADR-067]]).
// Offering the pane would put a phase's unfinished work in front of a reader as
// though it were finished: the pane would render "no readings of this feature"
// forever, and that message is one the application produces honestly for a real
// absence, so a reader could not tell the two apart.
//
// Every entry's `feature` must be a name the registry knows. That is checked
// from the Python suite (`tests/unit/features/test_pane_features.py`), because
// this list and the registry are the two halves and neither can check itself: a
// pane naming a feature nobody records shows "no readings of this feature"
// forever, which reads as a quiet market rather than as a typo.
export const PANES: readonly Pane[] = [
  { feature: "cvd", label: "CVD" },
  { feature: "ofi_1m", label: "OFI (1m)" },
  { feature: "depth_imbalance_10", label: "Depth imbalance (10)" },
  { feature: "open_interest_usd", label: "Open interest" },
  { feature: "funding_z", label: "Funding (z)" },
  { feature: "basis_bps", label: "Basis (bps)" },
  { feature: "liquidation_imbalance_5m", label: "Liquidations (5m)" },
  { feature: "dex_swap_imbalance", label: "DEX swap imbalance" },
];

export interface PanePoint {
  at_ns: number;
  value: number;
}

/**
 * `ok` — there is something to draw.
 * `empty` — the series carried no points at all.
 * `unavailable` — there were points and none carried this feature.
 *
 * Three states rather than one blank. They are three different facts, and the
 * main chart already refuses to collapse them (REQ-WP-009's FR-016); a pane
 * that showed one blank for all three would quietly undo that.
 */
export type PaneState = "ok" | "empty" | "unavailable";

export interface PaneSeries {
  points: readonly PanePoint[];
  state: PaneState;
  note: string;
}

export function paneSeries(points: readonly FeaturePointOut[], feature: string): PaneSeries {
  if (points.length === 0) {
    return {
      points: [],
      state: "empty",
      note: "No feature points in this window.",
    };
  }

  // Keyed by instant, last write winning: two points at one instant is the API
  // reporting a correction, and taking the last is a decision rather than a
  // property of the sort's stability.
  const byInstant = new Map<number, number>();
  for (const point of points) {
    const value = point.values[feature];
    if (value === undefined) {
      // The gap. Not a zero, not a carried-forward previous value: silence.
      continue;
    }
    byInstant.set(point.at_ns, value);
  }

  if (byInstant.size === 0) {
    return {
      points: [],
      state: "unavailable",
      // Deliberately different words from the empty case: a reader who sees
      // this should look for the feature, not for the window.
      note: `No ${feature} readings among these points.`,
    };
  }

  const drawn = [...byInstant.entries()]
    .map(([at_ns, value]) => ({ at_ns, value }))
    .sort((a, b) => a.at_ns - b.at_ns);

  return { points: drawn, state: "ok", note: "" };
}
