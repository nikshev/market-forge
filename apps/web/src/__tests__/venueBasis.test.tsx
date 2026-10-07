// @trace: REQ-WP-091
//
// The viewed venue's basis to the consensus, `10000 * (mid_i / consensus_mid - 1)`, as a lower pane.
//
// The pane is a feature name like any other, so nothing here is new machinery: `venue_basis_bps` was added to
// `PANES` when the pane list grew to ten (T006), and the API merges its values into the feature points the
// page already loads (T013). What these tests pin is that the name is really in the row with its own label,
// that the generic `paneSeries` draws it one point per instant in order, and that `availablePanes` -- the one
// definition of "has data" -- lights it up only when some point actually carries it, so an unbuilt producer
// still reads "no data" rather than a quiet market.
//
// It carries its own name because `basis_bps` in the same row is a different quantity: the derivatives basis,
// perp against spot. Confusing the two would draw one as the other.

import { describe, expect, it } from "vitest";

import { availablePanes, paneSeries, PANES, ROW } from "../panes";
import type { FeaturePointOut } from "../types";

const SECOND_NS = 1_000_000_000n;
const BASE_NS = 1788838800000000000n;

function point(index: number, values: Record<string, number>): FeaturePointOut {
  return { at_ns: BASE_NS + BigInt(index) * SECOND_NS, values };
}

describe("the venue basis pane", () => {
  it("draws ok, one point per instant in order, from the values the points carry", () => {
    // Given instants out of order, as a corrected backfill would arrive, and two readings at one instant,
    // which is a correction: the last one wins, so the pane never draws two lines through one moment.
    const points = [
      point(2, { venue_basis_bps: -7.5 }),
      point(0, { venue_basis_bps: 12.25 }),
      point(0, { venue_basis_bps: 5 }),
      point(1, { venue_basis_bps: 0 }),
    ];

    const drawn = paneSeries(points, "venue_basis_bps");

    expect(drawn.state).toBe("ok");
    expect(drawn.points.map((p) => p.value)).toEqual([5, 0, -7.5]);
    expect(drawn.points.map((p) => p.at_ns)).toEqual([
      BASE_NS,
      BASE_NS + SECOND_NS,
      BASE_NS + 2n * SECOND_NS,
    ]);
  });

  it("appears in availablePanes only when some point carries it, and reads no data when none does", () => {
    // A point carrying no basis is a gap, not a zero: a flat line through zero would say the venues were
    // exactly level, which is a claim about the market rather than about the data. That is why the state
    // under a series that carries nothing is `unavailable`, and the pane a reader sees today -- the
    // consensus worker does not write yet -- is a disabled "no data" button rather than a drawn line.
    const carrying = availablePanes([point(0, { cvd_base: 1 }), point(1, { venue_basis_bps: -4 })]);
    const notCarrying = availablePanes([point(0, { cvd_base: 1 }), point(1, { basis_bps: 20 })]);

    expect(carrying.has("venue_basis_bps")).toBe(true);
    expect(notCarrying.has("venue_basis_bps")).toBe(false);
    expect(paneSeries([point(0, { basis_bps: 20 })], "venue_basis_bps").state).toBe("unavailable");
    expect(availablePanes([]).has("venue_basis_bps")).toBe(false);
  });

  it("is in PANES and in ROW with the label a reader picks it by, apart from the derivatives basis", () => {
    expect(PANES.find((p) => p.feature === "venue_basis_bps")).toEqual({
      feature: "venue_basis_bps",
      label: "Venue basis (bps)",
    });
    expect(ROW.filter((p) => p.feature === "venue_basis_bps" || p.feature === "basis_bps")).toEqual([
      { feature: "basis_bps", label: "Basis (bps)" },
      { feature: "venue_basis_bps", label: "Venue basis (bps)" },
    ]);
  });
});
