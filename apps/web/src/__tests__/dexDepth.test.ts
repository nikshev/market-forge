// @trace: REQ-WP-054
//
// The band that declines to answer is what these tests are about. Every other
// overlay in this app draws a series that either exists or does not; a depth
// band can exist and say it never reached its target, and each stage between
// the table and the pixel is a chance to drop that.

import { describe, expect, it } from "vitest";

import {
  DOWN,
  DRAWN,
  EXHAUSTED,
  FAILED,
  NO_CURVE,
  REACHED,
  UP,
  bandsForSide,
  depthAgeNs,
  depthOverlay,
  furthestReachedBps,
} from "../dexDepth";
import type { DexDepthBandOut, DexDepthResponse } from "../types";

const STATE_TIME = 1_700_000_000_000_000_000n;

function band(overrides: Partial<DexDepthBandOut> = {}): DexDepthBandOut {
  return {
    side: UP,
    target_bps: "10",
    reachable: true,
    reached_bps: "10",
    amount0: "1.25",
    amount1: "3750.5",
    reference_price: "3000.1666",
    ticks_crossed: 4,
    reason: "",
    ...overrides,
  };
}

function response(bands: DexDepthBandOut[], stateTimeNs: bigint = STATE_TIME): DexDepthResponse {
  return {
    chain_id: 1,
    pool: "0xpool",
    requested_at_ns: STATE_TIME + 1_000n,
    state_time_ns: bands.length === 0 ? null : stateTimeNs,
    bands,
  };
}

describe("a band that never reached its target", () => {
  it("is drawn rather than omitted", () => {
    // Omitting it would be the same lie by absence: a chart with no 100 bps
    // band reads as a chart nobody asked about 100 bps.
    const overlay = depthOverlay({
      ok: true,
      value: response([
        band({ target_bps: "10" }),
        band({ target_bps: "100", reachable: false, reached_bps: "17.5", reason: "ran out" }),
      ]),
    });
    expect(overlay.bands).toHaveLength(2);
    expect(overlay.bands.map((b) => b.targetBps)).toEqual([10, 100]);
  });

  it("is distinguishable from one that was reached", () => {
    const overlay = depthOverlay({
      ok: true,
      value: response([
        band({ target_bps: "10" }),
        band({ target_bps: "100", reachable: false, reached_bps: "17.5", reason: "ran out" }),
      ]),
    });
    const [reached, exhausted] = overlay.bands;
    expect(reached.role).toBe(REACHED);
    expect(exhausted.role).toBe(EXHAUSTED);
    expect(reached.role).not.toBe(exhausted.role);
  });

  it("says how far the book actually went", () => {
    // Which is the whole reason it is worth a place on the chart: without it,
    // an exhausted band is a target and a notional that do not correspond.
    const overlay = depthOverlay({
      ok: true,
      value: response([
        band({ target_bps: "100", reachable: false, reached_bps: "17.5", reason: "ran out" }),
      ]),
    });
    const [only] = overlay.bands;
    expect(only.reachedBps).toBe(17.5);
    expect(only.reachedBps).toBeLessThan(only.targetBps);
    expect(only.reason).toBe("ran out");
  });

  it("keeps a reached band's two figures in agreement", () => {
    const overlay = depthOverlay({ ok: true, value: response([band({ target_bps: "25", reached_bps: "25" })]) });
    const [only] = overlay.bands;
    expect(only.reachedBps).toBe(only.targetBps);
  });
});

describe("a failure is not an empty pool", () => {
  it("says the load failed, and draws nothing", () => {
    // FR-016: a failed load must never be drawn as though it were data, and on
    // a chart an absent overlay and an empty one look identical.
    const overlay = depthOverlay({ ok: false, error: "HTTP 503" });
    expect(overlay.state).toBe(FAILED);
    expect(overlay.bands).toEqual([]);
    expect(overlay.notice).toContain("HTTP 503");
  });

  it("says so differently from a pool with no curve", () => {
    const failed = depthOverlay({ ok: false, error: "HTTP 503" });
    const absent = depthOverlay({ ok: true, value: response([]) });
    expect(absent.state).toBe(NO_CURVE);
    expect(absent.bands).toEqual([]);
    expect(absent.notice).not.toBe(failed.notice);
    expect(absent.notice).toBeTruthy();
  });

  it("draws nothing without a notice only when something is drawn", () => {
    const drawn = depthOverlay({ ok: true, value: response([band()]) });
    expect(drawn.state).toBe(DRAWN);
    expect(drawn.notice).toBeNull();
  });
});

describe("how stale the curve is", () => {
  it("is the cursor's instant against the curve's own", () => {
    // The two differ whenever the most recent curve predates the cursor, and a
    // reader who could not tell would have no way to know how stale the overlay
    // is.
    const overlay = depthOverlay({ ok: true, value: response([band()]) });
    expect(overlay.stateTimeNs).toBe(STATE_TIME);
    // Exact. Read as a JavaScript number this subtraction gives 5120: the
    // timestamp is 1.7e18 against a safe maximum of 9.0e15, so the values
    // quantise to the nearest 256 nanoseconds.
    expect(depthAgeNs(overlay, STATE_TIME + 5_000n)).toBe(5_000n);
    expect(Number(STATE_TIME) + 5_000 - Number(STATE_TIME)).not.toBe(5_000);
  });

  it("is unanswerable when nothing is drawn", () => {
    expect(depthAgeNs(depthOverlay({ ok: false, error: "x" }), STATE_TIME)).toBeNull();
    expect(depthAgeNs(depthOverlay({ ok: true, value: response([]) }), STATE_TIME)).toBeNull();
  });
});

describe("reading one side", () => {
  const overlay = depthOverlay({
    ok: true,
    value: response([
      band({ side: UP, target_bps: "100", reachable: false, reached_bps: "17.5" }),
      band({ side: UP, target_bps: "10" }),
      band({ side: DOWN, target_bps: "10" }),
      band({ side: DOWN, target_bps: "100" }),
    ]),
  });

  it("returns that side's bands in increasing distance", () => {
    expect(bandsForSide(overlay, UP).map((b) => b.targetBps)).toEqual([10, 100]);
    expect(bandsForSide(overlay, DOWN).map((b) => b.targetBps)).toEqual([10, 100]);
  });

  it("names the furthest band the book actually reached", () => {
    // Computed here so no caller re-derives "furthest reached" and gets it from
    // the target instead.
    expect(furthestReachedBps(overlay, UP)).toBe(10);
    expect(furthestReachedBps(overlay, DOWN)).toBe(100);
  });

  it("says nothing was reached rather than naming a band that was not", () => {
    const thin = depthOverlay({
      ok: true,
      value: response([band({ target_bps: "10", reachable: false, reached_bps: "3" })]),
    });
    expect(furthestReachedBps(thin, UP)).toBeNull();
  });
});

describe("amounts", () => {
  it("stay in the token that was spent", () => {
    // Converting here would need the reference price and would bake one axis
    // into the data -- and comparing token0 against token1 directly is the
    // mistake that once reported every pool as asymmetric.
    const overlay = depthOverlay({ ok: true, value: response([band()]) });
    const [only] = overlay.bands;
    expect(only.amount0).toBe(1.25);
    expect(only.amount1).toBe(3750.5);
    expect(only.referencePrice).toBe(3000.1666);
  });
});
