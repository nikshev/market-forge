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
  // JavaScript number -- 1.7e18 against a safe maximum of 9.0e15, quantising to
  // the nearest 256 nanoseconds.
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
    stateTimeNs: stateTimeNs === null ? null : BigInt(stateTimeNs),
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
