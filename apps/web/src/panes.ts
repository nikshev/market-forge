// @trace: REQ-WP-027
// @trace: REQ-WP-030
// @trace: REQ-WP-063
// @trace: REQ-WP-084
// @trace: REQ-WP-085
// @trace: REQ-WP-088
// @trace: REQ-WP-091
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

import type { BarOut, FeaturePointOut } from "./types";

export interface Pane {
  /** The registered feature name, as the API returns it. */
  feature: string;
  /** What a reader picks it by. */
  label: string;
}

// PRD section 27.3 lists nine panes: volume, CVD, OFI, OI, funding, basis, liquidations, DEX swap
// imbalance and DEX active liquidity. This is how the page's row compares with it, and where each
// one's data comes from as of 2026-10-11 (REQ-WP-093 to REQ-WP-097):
//
//   volume                 present, first, in `BAR_PANES` below -- read from the bars, not a feature;
//   CVD (base)             here as `cvd_base` ([[REQ-WP-088]]): derived by the worker from the bars' stored
//                          aggressor split, in base units not notional ([[ADR-068]]);
//   OFI (1m)               here, from [[REQ-WP-027]]; written by the worker from the per-minute book
//                          summaries the collectors store ([[REQ-WP-095]]) -- a once-a-second sampled
//                          top-of-book measure, not the exchange's event-level figure;
//   OI, funding, basis     here, from [[REQ-WP-030]]; written by the worker from the collectors' REST
//                          polls of each venue's perpetual ([[REQ-WP-093]]); the Binance series are spot
//                          and are shown their venue's perpetual;
//   liquidations           here, from [[REQ-WP-030]]; written by the worker from each venue's liquidation
//                          stream, and only for windows the stream was known to be listening to
//                          ([[REQ-WP-094]]);
//   venue basis            here as `venue_basis_bps`, from [[REQ-WP-091]]: the viewed venue's basis to the
//                          market-type consensus, `10000 * (mid_i / consensus_mid - 1)`. Its own name because
//                          `basis_bps` above is a different quantity (perp against spot), and not §27.3's list
//                          either, like the depth imbalance pane. The consensus is written every minute
//                          ([[REQ-WP-096]]): Bybit and OKX BTC are one perpetual group; the Binance and OKX
//                          spot series are the spot groups, two venues each ([[REQ-WP-098]]);
//   DEX swap imbalance,
//   DEX active liquidity   here, from [[REQ-WP-059]] and [[REQ-WP-063]], read from HyperEVM's two WHYPE/USDC
//                          pools ([[REQ-WP-099]]) and written for **the two HYPE perpetuals only** (Bybit and OKX), the
//                          markets the pools price; on any other series they read "no data" (no pool);
//   Depth imbalance (10)   **not in §27.3**: a pane this deployment added beyond the PRD's list, from
//                          [[REQ-WP-027]]; written with the OFI from the same minute summaries. Whether to
//                          keep it is the owner's call and it is left in place.
//
// An earlier version of this comment said all nine of §27.3 were here. They were not: volume was missing and
// depth imbalance stood in its place.
//
// A pane naming a feature nobody records renders "no readings of this feature" forever -- the message this
// app produces honestly for a real absence -- so a reader cannot tell an unbuilt pane from a quiet market.
// That is what [[REQ-WP-084]]'s "no data" is for.
//
// Every entry's `feature` must be a name the registry knows. That is checked
// from the Python suite (`tests/unit/features/test_pane_features.py`), because
// this list and the registry are the two halves and neither can check itself: a
// pane naming a feature nobody records shows "no readings of this feature"
// forever, which reads as a quiet market rather than as a typo. Volume is not a feature, which is why it is
// not an entry here but in `BAR_PANES`.
export const PANES: readonly Pane[] = [
  { feature: "cvd_base", label: "CVD (base)" },
  { feature: "ofi_1m", label: "OFI (1m)" },
  { feature: "depth_imbalance_10", label: "Depth imbalance (10)" },
  { feature: "open_interest_usd", label: "Open interest" },
  { feature: "funding_z", label: "Funding (z)" },
  { feature: "basis_bps", label: "Basis (bps)" },
  { feature: "venue_basis_bps", label: "Venue basis (bps)" },
  { feature: "liquidation_imbalance_5m", label: "Liquidations (5m)" },
  { feature: "dex_swap_imbalance", label: "DEX swap imbalance" },
  { feature: "dex_active_liquidity", label: "DEX active liquidity" },
];

/**
 * Panes whose values come from the loaded bars rather than the feature series (REQ-WP-085). Volume is a
 * property of the bar -- every `BarOut` carries `volume_base` -- so it needs no producer, and it is listed
 * apart from `PANES` because that list is checked against the feature registry.
 */
export const BAR_PANES: readonly Pane[] = [{ feature: "volume", label: "Volume" }];

/** What the pane row renders and the selection walks: volume first, as §27.3 lists it, then the features. */
export const ROW: readonly Pane[] = [...BAR_PANES, ...PANES];

export const isBarPane = (feature: string): boolean => BAR_PANES.some((p) => p.feature === feature);

export interface PanePoint {
  at_ns: bigint;
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
  // Keyed by `bigint`, which compares by value: two instants 100 nanoseconds
  // apart are two keys. As numbers they were one, and the rule below would have
  // dropped a point while calling it a correction (REQ-WP-061).
  const byInstant = new Map<bigint, number>();
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
    .sort((a, b) => (a.at_ns < b.at_ns ? -1 : a.at_ns > b.at_ns ? 1 : 0));

  return { points: drawn, state: "ok", note: "" };
}

/**
 * Volume per bar, from the loaded bars (REQ-WP-085).
 *
 * Final bars only: a forming bar's volume will change, and the chart already declines to treat such a bar as
 * finished. A final bar in which nothing traded has volume `0`, which is data -- the bar exists and was quiet
 * -- and is a point at zero. A `volume_base` that is not a finite number is skipped, never drawn as zero: a
 * zero is a claim about the market. Each value sits at the instant its bar starts, which is not when its
 * volume became known (the bar's close).
 */
export function volumeSeries(bars: readonly BarOut[]): PaneSeries {
  const drawn = bars
    .filter((bar) => bar.is_final)
    .flatMap((bar) => {
      const value = Number(bar.volume_base);
      return bar.volume_base.trim() !== "" && Number.isFinite(value)
        ? [{ at_ns: bar.open_time_ns, value }]
        : [];
    })
    .sort((a, b) => (a.at_ns < b.at_ns ? -1 : a.at_ns > b.at_ns ? 1 : 0));

  return drawn.length === 0
    ? { points: [], state: "empty", note: "No finished bars in this window." }
    : { points: drawn, state: "ok", note: "" };
}

/**
 * Which of the panes have anything behind them, for the view the page loaded (REQ-WP-084).
 *
 * "Has data" is `paneSeries`'s own definition -- some point carries a number under the feature's name -- and
 * not a second one written here. It is read from the series the page already loads, so a feature producer
 * added later makes its pane live with no change to the page, and no list of "built" features exists to drift.
 * A feature name that is not one of the panes gets no pane.
 */
export function availablePanes(
  points: readonly FeaturePointOut[],
  bars: readonly BarOut[] = [],
): ReadonlySet<string> {
  const available = new Set(
    PANES.filter((pane) => paneSeries(points, pane.feature).state === "ok").map((pane) => pane.feature),
  );
  if (volumeSeries(bars).state === "ok") {
    available.add("volume");
  }
  return available;
}

/**
 * Where the selection goes once it is known which panes have data.
 *
 * A choice that still has data is kept: the page never overrides a reader. Otherwise the first pane in the
 * row that has data, and `null` when none does. While it is not known (`null`) the choice is left alone --
 * a load in flight is not an absence.
 */
export function chooseSelection(
  current: string | null,
  available: ReadonlySet<string> | null,
): string | null {
  if (available === null) {
    return current;
  }
  if (current !== null && available.has(current)) {
    return current;
  }
  return ROW.find((pane) => available.has(pane.feature))?.feature ?? null;
}

/**
 * Splits a drawn series where the feature's own `cvd_run` changes (REQ-WP-088).
 *
 * A running sum is not comparable across a missing bar or a missed trade, and a line joined across the
 * break would say it is. Each run is its own segment. A series with no run information (every other
 * feature) is one segment; a point without a value for the feature is a gap in the series and not a break.
 */
export function segments(
  drawn: readonly PanePoint[],
  points: readonly FeaturePointOut[],
): PanePoint[][] {
  const runAt = new Map<bigint, number>();
  for (const point of points) {
    const run = point.values["cvd_run"];
    if (run !== undefined) {
      runAt.set(point.at_ns, run);
    }
  }
  const result: PanePoint[][] = [];
  let currentRun: number | undefined;
  for (const point of drawn) {
    const run = runAt.get(point.at_ns);
    const last = result.at(-1);
    if (last === undefined || (run !== undefined && currentRun !== undefined && run !== currentRun)) {
      result.push([point]);
    } else {
      last.push(point);
    }
    if (run !== undefined) {
      currentRun = run;
    }
  }
  return result;
}
