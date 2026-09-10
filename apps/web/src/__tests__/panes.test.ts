// @trace: REQ-WP-027
//
// PRD section 27.3's lower panes, for the three Phase 2 has data for.
//
// The decision about what to draw is tested here rather than through a
// component, for the reason `series.ts` already records: lightweight-charts
// needs a laid-out container and jsdom does not provide one, so a component
// test can never see a line.

import { describe, expect, it } from "vitest";

import { PANES, paneSeries } from "../panes";
import type { FeaturePointOut } from "../types";

const SECOND_NS = 1_000_000_000;
const BASE_NS = 1788838800000000000;

function point(index: number, values: Record<string, number>): FeaturePointOut {
  return { at_ns: BASE_NS + index * SECOND_NS, values };
}

describe("the pane list", () => {
  it("offers the panes whose phases have finished their data", () => {
    // Order flow from [[REQ-WP-027]], derivatives from [[REQ-WP-030]]. The DEX
    // pair is absent because Phase 4's data is, and offering an empty pane
    // would put unfinished work in front of a reader as though it were done.
    expect(PANES.map((p) => p.feature)).toEqual([
      "cvd",
      "ofi_1m",
      "depth_imbalance_10",
      "open_interest_usd",
      "funding_z",
      "basis_bps",
      "liquidation_imbalance_5m",
    ]);
  });

  it("gives every pane a label a reader can choose by", () => {
    for (const pane of PANES) {
      expect(pane.label.length).toBeGreaterThan(0);
    }
  });
});

describe("what a pane draws", () => {
  it("draws only the feature it names", () => {
    const points = [point(0, { cvd: 5, ofi_1m: -3 }), point(1, { cvd: 7, ofi_1m: 2 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.state).toBe("ok");
    expect(drawn.points.map((p) => p.value)).toEqual([5, 7]);
  });

  it("leaves a gap where a point carries no value for it", () => {
    // The rule the whole requirement exists for. A flat line through zero in a
    // CVD pane says "no net delta", which is a claim about the market rather
    // than about the data.
    const points = [point(0, { cvd: 5 }), point(1, { ofi_1m: 2 }), point(2, { cvd: 9 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.points).toHaveLength(2);
    expect(drawn.points.map((p) => p.value)).toEqual([5, 9]);
  });

  it("draws a real zero", () => {
    // The other half of the same rule. Dropping missing values is easy if you
    // also drop zeros; this is what stops that.
    const points = [point(0, { cvd: 0 }), point(1, {}), point(2, { cvd: -2 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.points.map((p) => p.value)).toEqual([0, -2]);
  });

  it("begins where the feature begins", () => {
    const points = [point(0, {}), point(1, {}), point(2, { cvd: 4 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.points).toHaveLength(1);
    expect(drawn.points[0]?.at_ns).toBe(BASE_NS + 2 * SECOND_NS);
  });

  it("orders by instant whatever order it was given", () => {
    const points = [point(2, { cvd: 3 }), point(0, { cvd: 1 }), point(1, { cvd: 2 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.points.map((p) => p.value)).toEqual([1, 2, 3]);
  });

  it("takes the last of two points at one instant", () => {
    // Stated rather than left to the sort's stability, which is a property of
    // the runtime rather than of this decision.
    const points = [point(0, { cvd: 1 }), point(0, { cvd: 9 })];

    const drawn = paneSeries(points, "cvd");

    expect(drawn.points.map((p) => p.value)).toEqual([9]);
  });

  it("draws a single reading", () => {
    const drawn = paneSeries([point(0, { cvd: 4 })], "cvd");

    expect(drawn.state).toBe("ok");
    expect(drawn.points).toHaveLength(1);
  });
});

describe("what a pane says when it has nothing to draw", () => {
  it("distinguishes no points from no values for this feature", () => {
    const nothing = paneSeries([], "cvd");
    const silent = paneSeries([point(0, { ofi_1m: 1 })], "cvd");

    expect(nothing.state).toBe("empty");
    expect(silent.state).toBe("unavailable");
    expect(nothing.state).not.toBe(silent.state);
  });

  it("says something a reader can act on in each case", () => {
    expect(paneSeries([], "cvd").note).not.toBe("");
    expect(paneSeries([point(0, {})], "cvd").note).not.toBe("");
  });

  it("carries no points in either case, so nothing can be drawn by accident", () => {
    expect(paneSeries([], "cvd").points).toHaveLength(0);
    expect(paneSeries([point(0, {})], "cvd").points).toHaveLength(0);
  });
});
