// @trace: REQ-WP-084
//
// The chart shows candidate extrema only when asked. The decision is `extremumMarkers`' `includeCandidates`,
// so it goes through the same filter that already withholds a candidate nobody could have seen yet: the switch
// widens the view, it never looks ahead (Principle I).

import { describe, expect, it } from "vitest";

import { extremumMarkers } from "../extrema";
import { AS_SEEN_THEN, CURRENT_REFIT } from "../types";
import type { ConfirmedExtremumOut, ExtremumCandidateOut } from "../types";

const MINUTE_NS = 60_000_000_000n;
const BASE_NS = 1788838800000000000n;
const at = (minutes: number): bigint => BASE_NS + BigInt(minutes) * MINUTE_NS;

function turn(turnAt: number, knownAt: number, extras: Partial<ConfirmedExtremumOut> = {}) {
  return {
    extremum_id: `turn-${turnAt}`,
    extremum_type: "HIGH",
    extremum_time_ns: at(turnAt),
    known_at_ns: at(knownAt),
    price: "112000.10",
    confirmation_lag_bars: knownAt - turnAt,
    prominence_bps: null,
    source_candidate_id: null,
    ...extras,
  } satisfies ConfirmedExtremumOut;
}

function candidate(time: number, observed: number, id = `cand-${time}`): ExtremumCandidateOut {
  return {
    candidate_id: id,
    candidate_type: "LOW",
    candidate_time_ns: at(time),
    observed_at_ns: at(observed),
    price: "111000.00",
    structural_score: 0.4,
  };
}

const CONFIRMED = [turn(1, 3), turn(5, 7), turn(9, 11)];
const CANDIDATES = [candidate(2, 3), candidate(4, 5), candidate(6, 7), candidate(8, 9)];

describe("candidate extrema, off or on", () => {
  it("draws only the confirmed turns when candidates are not included", () => {
    const marks = extremumMarkers({
      confirmed: CONFIRMED,
      candidates: CANDIDATES,
      mode: CURRENT_REFIT,
      atNs: at(20),
      includeCandidates: false,
    });

    expect(marks).toHaveLength(3);
    expect(marks.every((m) => m.kind === "confirmed")).toBe(true);
  });

  it("draws the same three and the four candidates when they are included", () => {
    const off = extremumMarkers({
      confirmed: CONFIRMED,
      candidates: CANDIDATES,
      mode: CURRENT_REFIT,
      atNs: at(20),
      includeCandidates: false,
    });
    const on = extremumMarkers({
      confirmed: CONFIRMED,
      candidates: CANDIDATES,
      mode: CURRENT_REFIT,
      atNs: at(20),
      includeCandidates: true,
    });

    expect(on).toHaveLength(7);
    expect(on.filter((m) => m.kind === "confirmed")).toEqual(off);
  });

  it("keeps the old meaning when the argument is left out, so existing callers are unchanged", () => {
    const marks = extremumMarkers({
      confirmed: CONFIRMED,
      candidates: CANDIDATES,
      mode: CURRENT_REFIT,
      atNs: at(20),
    });

    expect(marks).toHaveLength(7);
  });

  it("still withholds, in AS-SEEN-THEN, a candidate observed after the instant even when included", () => {
    // Observed at minute 9 against an instant at minute 6: nobody could have seen it then.
    const marks = extremumMarkers({
      confirmed: [],
      candidates: [candidate(2, 3), candidate(8, 9)],
      mode: AS_SEEN_THEN,
      atNs: at(6),
      includeCandidates: true,
    });

    expect(marks.map((m) => m.at_ns)).toEqual([at(2)]);
  });

  it("keeps a candidate that became a shown confirmation as one turn, not two", () => {
    const marks = extremumMarkers({
      confirmed: [turn(2, 3, { source_candidate_id: "cand-2" })],
      candidates: [candidate(2, 3, "cand-2")],
      mode: CURRENT_REFIT,
      atNs: at(20),
      includeCandidates: true,
    });

    expect(marks).toHaveLength(1);
    expect(marks[0]?.kind).toBe("confirmed");
  });

  it("includes nothing with nothing returned, on or off", () => {
    for (const includeCandidates of [false, true]) {
      expect(
        extremumMarkers({
          confirmed: [],
          candidates: [],
          mode: AS_SEEN_THEN,
          atNs: at(1),
          includeCandidates,
        }),
      ).toEqual([]);
    }
  });
});
