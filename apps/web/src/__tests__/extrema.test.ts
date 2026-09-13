// @trace: REQ-WP-028
//
// PRD section 27.2's markers for candidate versus confirmed extrema.
//
// The decision is tested here rather than through a component, for the reason
// `series.ts` records: lightweight-charts needs a laid-out container and jsdom
// does not provide one.

import { describe, expect, it } from "vitest";

import { extremumMarkers } from "../extrema";
import { AS_SEEN_THEN, CURRENT_REFIT } from "../types";
import type { ConfirmedExtremumOut, ExtremumCandidateOut } from "../types";

const MINUTE_NS = 60_000_000_000n;
const BASE_NS = 1788838800000000000n;

function turn(
  turnAt: number,
  knownAt: number,
  extras: Partial<ConfirmedExtremumOut> = {},
): ConfirmedExtremumOut {
  return {
    extremum_id: `turn-${turnAt}`,
    extremum_type: "HIGH",
    extremum_time_ns: BASE_NS + BigInt(turnAt) * MINUTE_NS,
    known_at_ns: BASE_NS + BigInt(knownAt) * MINUTE_NS,
    price: "112000.10",
    confirmation_lag_bars: knownAt - turnAt,
    prominence_bps: null,
    source_candidate_id: null,
    ...extras,
  };
}

function candidate(at: number, observed: number, id = `cand-${at}`): ExtremumCandidateOut {
  return {
    candidate_id: id,
    candidate_type: "LOW",
    candidate_time_ns: BASE_NS + BigInt(at) * MINUTE_NS,
    observed_at_ns: BASE_NS + BigInt(observed) * MINUTE_NS,
    price: "111000.00",
    structural_score: 0.4,
  };
}

describe("what the chart may show about turns", () => {
  it("draws a confirmed turn where it happened", () => {
    const marks = extremumMarkers({
      confirmed: [turn(10, 14)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 20n * MINUTE_NS,
    });

    expect(marks).toHaveLength(1);
    expect(marks[0]?.at_ns).toBe(BASE_NS + 10n * MINUTE_NS);
    expect(marks[0]?.kind).toBe("confirmed");
  });

  it("hides a turn the system did not yet know about", () => {
    // PRD section 45's Phase 1A acceptance. A marker at minute 10, read as seen
    // at minute 13, claims the system knew about a turn before it did.
    const marks = extremumMarkers({
      confirmed: [turn(10, 14)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 13n * MINUTE_NS,
    });

    expect(marks).toEqual([]);
  });

  it("shows it at the instant it became knowable, not one later", () => {
    const marks = extremumMarkers({
      confirmed: [turn(10, 14)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 14n * MINUTE_NS,
    });

    expect(marks).toHaveLength(1);
  });

  it("hides a candidate observed after the instant asked about", () => {
    // The criterion names confirmations only; a candidate leaking in early is
    // the same defect under a different name.
    const marks = extremumMarkers({
      confirmed: [],
      candidates: [candidate(10, 12)],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 11n * MINUTE_NS,
    });

    expect(marks).toEqual([]);
  });

  it("tells a candidate apart from a confirmation", () => {
    const marks = extremumMarkers({
      confirmed: [turn(10, 12)],
      candidates: [candidate(20, 21)],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 30n * MINUTE_NS,
    });

    expect(marks.map((m) => m.kind).sort()).toEqual(["candidate", "confirmed"]);
  });

  it("does not draw a candidate twice once its confirmation arrives", () => {
    // One turn happened. Two markers would say two did.
    const marks = extremumMarkers({
      confirmed: [turn(10, 12, { source_candidate_id: "cand-10" })],
      candidates: [candidate(10, 11, "cand-10")],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 30n * MINUTE_NS,
    });

    expect(marks).toHaveLength(1);
    expect(marks[0]?.kind).toBe("confirmed");
  });

  it("still draws a candidate that was never confirmed", () => {
    // A swing that did not confirm is a fact about the market. Dropping it as
    // noise makes the detector look better than it is.
    const marks = extremumMarkers({
      confirmed: [],
      candidates: [candidate(20, 21)],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 30n * MINUTE_NS,
    });

    expect(marks).toHaveLength(1);
    expect(marks[0]?.kind).toBe("candidate");
  });

  it("orders markers by the instant they mark", () => {
    const marks = extremumMarkers({
      confirmed: [turn(30, 31), turn(10, 11)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: BASE_NS + 40n * MINUTE_NS,
    });

    expect(marks.map((m) => m.at_ns)).toEqual([
      BASE_NS + 10n * MINUTE_NS,
      BASE_NS + 30n * MINUTE_NS,
    ]);
  });

  it("applies no knowledge filter in CURRENT REFIT", () => {
    // PRD section 27.5 makes that mode the place where repaint-like differences
    // are meant to be visible. Filtering there would hide the very difference
    // the mode exists to expose.
    const marks = extremumMarkers({
      confirmed: [turn(10, 14)],
      candidates: [],
      mode: CURRENT_REFIT,
      atNs: BASE_NS + 13n * MINUTE_NS,
    });

    expect(marks).toHaveLength(1);
  });

  it("returns nothing when there is nothing, without inventing a marker", () => {
    expect(
      extremumMarkers({ confirmed: [], candidates: [], mode: AS_SEEN_THEN, atNs: BASE_NS }),
    ).toEqual([]);
  });
});
