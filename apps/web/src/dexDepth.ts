// @trace: REQ-WP-054
//
// PRD section 27.2 lists "DEX liquidity bands" among the chart's toggle layers.
// As with `volumeProfile.ts`, the decision about what to draw lives here and is
// tested; the drawing itself is the library's problem, and jsdom has no layout
// engine for a component test to see it through.
//
// **The whole point of this module is that a band can decline to answer.** Every
// other overlay draws a series that either exists or does not. A depth band can
// exist *and* say it never reached its target: ADR-036's distinction, where the
// amounts then describe exhausting the known liquidity rather than reaching the
// band. Drawn the same as a reached band it reads as a cheaper market than
// exists; omitted, it reads as a band nobody asked about. So it is drawn, and
// drawn differently.

import type { DexDepthBandOut, DexDepthResponse } from "./types";

export const REACHED = "reached";
export const EXHAUSTED = "exhausted";
export type BandRole = typeof REACHED | typeof EXHAUSTED;

export const UP = "up";
export const DOWN = "down";

export interface DepthBand {
  side: string;
  targetBps: number;
  // `reached` when the walk got there; `exhausted` when the book ran out first.
  role: BandRole;
  // Where the book actually got to. Equal to `targetBps` on a reached band, and
  // short of it on an exhausted one -- which is what makes the exhausted band
  // worth a place on the chart rather than a gap.
  reachedBps: number;
  // What the move consumed, in the token that was spent. Not converted here:
  // the conversion needs the reference price and belongs to whoever is drawing
  // against a particular axis.
  amount0: number;
  amount1: number;
  referencePrice: number;
  reason: string;
}

export const NO_CURVE = "no-curve";
export const FAILED = "failed";
export const DRAWN = "drawn";
export type OverlayState = typeof NO_CURVE | typeof FAILED | typeof DRAWN;

export interface DepthOverlay {
  state: OverlayState;
  bands: DepthBand[];
  // The curve's own instant, not the one asked for. Null when there is no
  // curve, and worth showing whenever it is far from the cursor: an overlay
  // from an hour ago drawn on a chart at this minute is stale rather than
  // wrong, and a reader cannot tell without being told.
  //
  // A `bigint`, because a nanosecond epoch timestamp does not fit in a
  // JavaScript number -- 1.8e18 against a safe maximum of 9.0e15, quantising to
  // the nearest 256 nanoseconds. Parsed in `api.ts` now, along with every other
  // instant this app receives ([[REQ-WP-061]]); this module reads one.
  stateTimeNs: bigint | null;
  // Why nothing is drawn, when nothing is. Null when something is.
  notice: string | null;
}

function toBand(band: DexDepthBandOut): DepthBand {
  return {
    side: band.side,
    targetBps: Number(band.target_bps),
    role: band.reachable ? REACHED : EXHAUSTED,
    reachedBps: Number(band.reached_bps),
    amount0: Number(band.amount0),
    amount1: Number(band.amount1),
    referencePrice: Number(band.reference_price),
    reason: band.reason,
  };
}

// A response into what the chart draws.
//
// The three states are distinct on purpose. FR-016 of REQ-WP-009 says a failed
// load must never be drawn as though it were data, and on a chart an absent
// overlay and an empty one look identical -- so "the request failed" and "this
// pool has no curve yet" each get their own notice rather than both getting a
// blank layer.
export function depthOverlay(
  result: { ok: true; value: DexDepthResponse } | { ok: false; error: string },
): DepthOverlay {
  if (!result.ok) {
    return {
      state: FAILED,
      bands: [],
      stateTimeNs: null,
      notice: `depth could not be loaded — ${result.error}`,
    };
  }
  const { bands, state_time_ns: stateTimeNs } = result.value;
  if (bands.length === 0) {
    return {
      state: NO_CURVE,
      bands: [],
      stateTimeNs: null,
      notice: "no depth curve was recorded for this pool at this time",
    };
  }
  return {
    state: DRAWN,
    bands: bands.map(toBand),
    stateTimeNs,
    notice: null,
  };
}

// How stale the drawn curve is, in nanoseconds, or null when nothing is drawn.
//
// Separate from the overlay itself because staleness is a judgement the caller
// makes with a threshold this module does not know: a chart at one-minute bars
// tolerates more than one at one-second bars.
export function depthAgeNs(overlay: DepthOverlay, atNs: bigint): bigint | null {
  if (overlay.stateTimeNs === null) {
    return null;
  }
  return atNs - overlay.stateTimeNs;
}

// The bands of one side, in increasing distance from the reference price.
export function bandsForSide(overlay: DepthOverlay, side: string): DepthBand[] {
  return overlay.bands
    .filter((band) => band.side === side)
    .sort((a, b) => a.targetBps - b.targetBps);
}

// The furthest band the book actually reached on a side, or null when it
// reached none.
//
// This is the figure a reader wants when a curve is mostly exhausted, and
// computing it here keeps every caller from re-deriving "furthest reached" and
// one of them getting it from `targetBps`.
export function furthestReachedBps(overlay: DepthOverlay, side: string): number | null {
  const reached = bandsForSide(overlay, side).filter((band) => band.role === REACHED);
  if (reached.length === 0) {
    return null;
  }
  return Math.max(...reached.map((band) => band.targetBps));
}

// How stale is too stale.
//
// `depthAgeNs` computes the gap and deliberately leaves the judgement to a
// caller. Nothing was making that judgement, so an hour-old curve was drawn
// with exactly the confidence of a current one. This is where it is made, and
// the threshold is an argument rather than a literal so the boundary itself can
// be tested.
export const FRESH = "fresh";
export const STALE = "stale";
export const UNKNOWN = "unknown";
// The curve is *later* than the instant it is drawn at. A chart showing that is
// showing a reader something the moment it depicts could not have known --
// Constitution Principle I, on screen rather than in a feature. It is called
// out rather than folded into "fresh", which is what a plain magnitude
// comparison would have done.
export const AHEAD = "ahead";
export type Freshness = typeof FRESH | typeof STALE | typeof UNKNOWN | typeof AHEAD;

export interface DepthFreshness {
  state: Freshness;
  // Null whenever the state is `unknown`, and signed otherwise: negative is the
  // `ahead` case, and hiding the sign would hide the problem.
  ageNs: bigint | null;
}

// One minute.
//
// A depth curve is recomputed when the pool's state changes, so the tolerable
// age is a property of the chain rather than of the chart. HyperEVM produces a
// block a second and Ethereum one every twelve ([[REQ-WP-052]] measured both),
// so a minute is five Ethereum blocks and sixty HyperEVM ones -- long enough
// that a quiet pool is not flagged for having nothing happen, short enough that
// a curve nobody refreshed is not read as current.
export const STALE_AFTER_NS = 60_000_000_000n;

export function depthFreshness(
  overlay: DepthOverlay,
  atNs: bigint,
  staleAfterNs: bigint,
): DepthFreshness {
  const ageNs = depthAgeNs(overlay, atNs);
  if (ageNs === null) {
    return { state: UNKNOWN, ageNs: null };
  }
  if (ageNs < 0n) {
    return { state: AHEAD, ageNs };
  }
  return { state: ageNs > staleAfterNs ? STALE : FRESH, ageNs };
}

// What to tell a reader about the curve's age, or nothing when there is nothing
// to say. A fresh curve says nothing: a notice on every chart is a notice
// nobody reads.
export function freshnessNotice(freshness: DepthFreshness): string | null {
  switch (freshness.state) {
    case FRESH:
      return null;
    case UNKNOWN:
      return "this curve carries no time, so how current it is cannot be shown";
    case AHEAD:
      return `this curve is ${describeAge(-freshness.ageNs!)} later than the instant shown`;
    case STALE:
      return `this curve is ${describeAge(freshness.ageNs!)} old`;
  }
}

const NS_PER_SECOND = 1_000_000_000n;
const SECONDS_PER_MINUTE = 60n;
const MINUTES_PER_HOUR = 60n;

// Whole units, largest that fits. Arithmetic stays in `bigint` throughout: a
// nanosecond age converted to a number to be divided is the same quantisation
// this module exists to avoid, and an age is exactly the quantity somebody
// would be tempted to convert.
function describeAge(ageNs: bigint): string {
  const seconds = ageNs / NS_PER_SECOND;
  if (seconds < SECONDS_PER_MINUTE) {
    return `${seconds}s`;
  }
  const minutes = seconds / SECONDS_PER_MINUTE;
  if (minutes < MINUTES_PER_HOUR) {
    return `${minutes}m`;
  }
  return `${minutes / MINUTES_PER_HOUR}h`;
}
