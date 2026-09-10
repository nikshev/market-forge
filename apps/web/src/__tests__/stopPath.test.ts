// @trace: REQ-WP-032
//
// PRD section 44A.33's position view, and the rule underneath its field list:
// AS-SEEN-THEN must show the stop path exactly as generated, not recompute a
// prettier historical trail.
//
// Tested here rather than through a component for the reason `series.ts`
// records: lightweight-charts needs a laid-out container and jsdom has none.

import { describe, expect, it } from "vitest";

import { stopPath } from "../stopPath";
import { AS_SEEN_THEN, CURRENT_REFIT } from "../types";
import type { PositionOut, StopAnchorOut, StopProposalOut } from "../types";

const MINUTE_NS = 60 * 1_000_000_000;
const BASE_NS = 1788838800000000000;

const at = (minute: number) => BASE_NS + minute * MINUTE_NS;

const LONG: PositionOut = {
  position_id: "pos-1",
  side: "LONG",
  entry_time_ns: at(0),
  average_entry_price: "100.00",
  initial_stop_price: "90.00",
  hard_stop_price: "85.00",
  current_strategy_stop: "95.00",
};

function anchor(knownAt: number, price = "94.00"): StopAnchorOut {
  return {
    kind: "confirmed_swing",
    price,
    known_at_ns: at(knownAt),
    description: "a confirmed higher low",
  };
}

function moved(minute: number, price: string, anchoredAt = minute): StopProposalOut {
  return {
    at_ns: at(minute),
    price,
    phase: "STRUCTURE_TRAIL",
    reasons: ["STRUCTURAL_ANCHOR"],
    anchor: anchor(anchoredAt, price),
    moved: true,
    refused: false,
  };
}

function held(minute: number, price: string, reason: string): StopProposalOut {
  return {
    at_ns: at(minute),
    price,
    phase: "STRUCTURE_TRAIL",
    reasons: [reason],
    anchor: null,
    moved: false,
    refused: false,
  };
}

// --- the path is carried, not recomputed -------------------------------------

describe("the stop path", () => {
  it("is the same path whichever future followed it", () => {
    // The criterion no recomputing implementation can pass, and the reason it
    // is written as a comparison rather than against a fixed expected path: a
    // fixed path is satisfied by a recomputation that agrees on this input and
    // goes on being satisfied when the anchor logic changes underneath it.
    const proposals = [moved(1, "92.00"), held(2, "92.00", "HELD_COOLDOWN"), moved(3, "95.00")];

    const one = stopPath({
      position: LONG,
      proposals,
      excursion: { mfe_r: 2.1, mae_r: -0.4 },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });
    const other = stopPath({
      position: LONG,
      proposals,
      excursion: { mfe_r: 9.9, mae_r: -0.01 },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(one.path).toEqual(other.path);
    expect(one.path.map((p) => p.price)).toEqual(["92.00", "92.00", "95.00"]);
  });

  it("hides proposals later than the instant in AS-SEEN-THEN", () => {
    const view = stopPath({
      position: LONG,
      proposals: [moved(1, "92.00"), moved(5, "95.00")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(3),
    });

    expect(view.path.map((p) => p.at_ns)).toEqual([at(1)]);
  });

  it("shows a decision made at the instant itself", () => {
    // The boundary, and it falls the inclusive way: a decision made at `atNs`
    // was knowable at `atNs`. Excluding it hides the most recent stop update on
    // every chart drawn at the moment it happened -- which is every live chart.
    const view = stopPath({
      position: LONG,
      proposals: [moved(3, "95.00")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(3),
    });

    expect(view.path.map((p) => p.at_ns)).toEqual([at(3)]);
  });

  it("draws decisions in the order they were made, however they arrived", () => {
    // Nothing promises a stored path arrives sorted. Drawn in arrival order, a
    // staircase steps backwards through time and reads as a stop that moved
    // down and then up -- the one shape the monotonic rule forbids.
    const view = stopPath({
      position: LONG,
      proposals: [moved(3, "95.00"), moved(1, "92.00"), held(2, "92.00", "HELD_COOLDOWN")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path.map((p) => p.at_ns)).toEqual([at(1), at(2), at(3)]);
  });

  it("does not filter in CURRENT REFIT", () => {
    // Section 27.5 makes that mode the place repaint-like differences are meant
    // to be visible; filtering there hides the difference it exists to expose.
    const view = stopPath({
      position: LONG,
      proposals: [moved(1, "92.00"), moved(5, "95.00")],
      excursion: { mfe_r: null, mae_r: null },
      mode: CURRENT_REFIT,
      atNs: at(3),
    });

    expect(view.path).toHaveLength(2);
  });

  it("refuses a path whose anchor became knowable after the decision", () => {
    // The corrupted case, not the absent one. Dropping the anchor renders a
    // clean chart from a wrong path; drawing it renders the forbidden chart.
    const view = stopPath({
      position: LONG,
      proposals: [moved(1, "92.00", 4)],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.state).toBe("inconsistent");
    expect(view.path).toEqual([]);
    expect(view.note).toContain(String(at(1)));
  });
});

// --- a hold is not a gap -----------------------------------------------------

describe("holds", () => {
  it("are points on the path, not absences", () => {
    const view = stopPath({
      position: LONG,
      proposals: [held(1, "90.00", "HELD_NO_ANCHOR"), held(2, "90.00", "HELD_COOLDOWN")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path).toHaveLength(2);
    expect(view.path.every((p) => p.kind === "held")).toBe(true);
  });

  it("stay distinguishable from each other by their reasons", () => {
    // ADR-032 kept six kinds of hold apart in the model. A view drawing only
    // movements collapses them at the last step before a human reads them: a
    // stop held on a cooldown and one held because nothing was knowable are the
    // same flat line and different facts.
    const view = stopPath({
      position: LONG,
      proposals: [held(1, "90.00", "HELD_NO_ANCHOR"), held(2, "90.00", "HELD_COOLDOWN")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path.map((p) => p.reasons)).toEqual([["HELD_NO_ANCHOR"], ["HELD_COOLDOWN"]]);
  });

  it("carry a reason the view has never heard of", () => {
    // A dropped reason is a newly added veto that looks like no veto at all.
    //
    // The code deliberately shares no prefix with any reason this build knows.
    // An earlier version of this test used "HELD_SOMETHING_ADDED_LATER" and a
    // mutant that filtered reasons down to a known list survived it, because
    // the invented code still looked familiar enough to pass the filter.
    const view = stopPath({
      position: LONG,
      proposals: [held(1, "90.00", "VETOED_BY_A_RULE_WRITTEN_NEXT_YEAR")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path[0].reasons).toEqual(["VETOED_BY_A_RULE_WRITTEN_NEXT_YEAR"]);
  });

  it("keep an absent anchor absent", () => {
    const view = stopPath({
      position: LONG,
      proposals: [moved(1, "92.00"), held(2, "92.00", "HELD_NO_ANCHOR")],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path[1].anchor).toBeNull();
  });

  it("are a different kind from a refusal", () => {
    const refused: StopProposalOut = {
      ...held(1, "101.00", "REFUSED_BEYOND_MARKET"),
      refused: true,
    };
    const view = stopPath({
      position: LONG,
      proposals: [refused],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.path[0].kind).toBe("refused");
  });
});

// --- four levels, not two ----------------------------------------------------

describe("the levels", () => {
  it("are entry, initial, hard and current", () => {
    const view = stopPath({
      position: LONG,
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.levels).toEqual([
      { label: "entry", price: "100.00" },
      { label: "initial", price: "90.00" },
      { label: "hard", price: "85.00" },
      { label: "current", price: "95.00" },
    ]);
  });

  it("leave out a hard stop nobody set", () => {
    // Not equal to the initial stop: one line where the position has two says
    // there is less room below than there is.
    const view = stopPath({
      position: { ...LONG, hard_stop_price: null },
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.levels.map((l) => l.label)).toEqual(["entry", "initial", "current"]);
  });
});

// --- the figures -------------------------------------------------------------

describe("the figures", () => {
  it("read open risk from the position, with no path at all", () => {
    // The spec defect this requirement caught in its own planning: an unrun
    // policy does not mean unknown risk. Entry 100, initial stop 90, current
    // stop 95 -- half the accepted risk is still open, and the path says
    // nothing about it either way.
    const view = stopPath({
      position: LONG,
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.state).toBe("empty");
    expect(view.openRiskR).toBeCloseTo(0.5);
  });

  it("lock nothing while the stop is still under the entry", () => {
    // Zero is the true reading here, not an absence: the stop exists and it is
    // below entry, so the locked profit is exactly none.
    const view = stopPath({
      position: LONG,
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.lockedProfitR).toBe(0);
  });

  it("lock profit once the stop is beyond the entry", () => {
    const view = stopPath({
      position: { ...LONG, current_strategy_stop: "103.00" },
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.lockedProfitR).toBeCloseTo(0.3);
    expect(view.openRiskR).toBe(0);
  });

  it("report an excursion over nothing observed as unavailable, not zero", () => {
    const view = stopPath({
      position: LONG,
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.mfeR).toBeNull();
    expect(view.maeR).toBeNull();
    expect(view.note).toContain("no path");
  });

  it("measure a SHORT position the other way up", () => {
    const short: PositionOut = {
      ...LONG,
      side: "SHORT",
      average_entry_price: "100.00",
      initial_stop_price: "110.00",
      hard_stop_price: "115.00",
      current_strategy_stop: "105.00",
    };

    const view = stopPath({
      position: short,
      proposals: [],
      excursion: { mfe_r: null, mae_r: null },
      mode: AS_SEEN_THEN,
      atNs: at(10),
    });

    expect(view.openRiskR).toBeCloseTo(0.5);
    expect(view.lockedProfitR).toBe(0);
  });
});
