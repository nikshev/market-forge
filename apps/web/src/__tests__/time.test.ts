// @trace: REQ-WP-061
//
// The instants this app receives cannot be held in a `number`, and the four
// comparisons that decide what was knowable are the ones that would have been
// wrong. These tests are about the boundary and those four.

import { describe, expect, it } from "vitest";

import { extremumMarkers } from "../extrema";
import { paneSeries } from "../panes";
import { stopPath } from "../stopPath";
import {
  BadTime,
  chartMilliseconds,
  chartSeconds,
  duration,
  nanoseconds,
  nanosecondsFromIso,
  optionalNanoseconds,
} from "../time";
import { AS_SEEN_THEN } from "../types";
import type { ConfirmedExtremumOut, FeaturePointOut, PositionOut, StopProposalOut } from "../types";

// A real mark whose low digits are not a multiple of 256, so a double moves it.
const EXACT = 1789000000123456789n;

describe("an instant off the wire", () => {
  it("keeps every digit", () => {
    expect(nanoseconds(EXACT.toString(), "at_ns")).toBe(EXACT);
    // What a `number` field gave every consumer before this.
    expect(BigInt(Number(EXACT))).toBe(1789000000123456768n);
  });

  it("refuses an empty string rather than returning the epoch", () => {
    // `BigInt("")` is `0n`: 1970, which is positive, ordered and believable.
    expect(BigInt("")).toBe(0n);
    expect(() => nanoseconds("", "at_ns")).toThrow(BadTime);
  });

  it.each(["-1", "12.5", "1e9", "abc", " 1789", "1789 ", "0x10", "+5", "007", null, 5, undefined])(
    "refuses %p",
    (bad) => {
      expect(() => nanoseconds(bad, "at_ns")).toThrow(BadTime);
    },
  );

  it("allows a stated zero", () => {
    expect(nanoseconds("0", "at_ns")).toBe(0n);
  });

  it("passes a null through only where null is an answer", () => {
    expect(optionalNanoseconds(null, "state_time_ns")).toBeNull();
    expect(() => optionalNanoseconds("", "state_time_ns")).toThrow(BadTime);
  });
});

describe("a duration", () => {
  it("stays a number, and the bound is what makes that legitimate", () => {
    const week = 7 * 24 * 60 * 60 * 1_000_000_000;
    expect(duration(week, "timeframe_ns")).toBe(week);
    expect(Number.isSafeInteger(week)).toBe(true);
  });

  it("refuses what is not a span", () => {
    expect(() => duration("900000000000", "timeframe_ns")).toThrow(BadTime);
    expect(() => duration(-1, "timeframe_ns")).toThrow(BadTime);
    expect(() => duration(Number.MAX_SAFE_INTEGER + 2, "timeframe_ns")).toThrow(BadTime);
  });
});

describe("the narrowing", () => {
  it("divides in bigint, so the input is exact", () => {
    expect(chartSeconds(EXACT)).toBe(1789000000);
    expect(chartMilliseconds(EXACT)).toBe(1789000000123);
  });

  it("is the only place resolution is given up", () => {
    // Two marks a hundred nanoseconds apart are one second and one millisecond.
    // That is fine for an axis and is why the same conversion is forbidden in a
    // comparison.
    expect(chartSeconds(EXACT)).toBe(chartSeconds(EXACT + 100n));
  });

  it("converts an ISO instant without going through a float", () => {
    expect(nanosecondsFromIso("2026-09-06T11:15:00Z")).toBe(1788693300000000000n);
    expect(nanosecondsFromIso("not a date")).toBeNull();
  });
});

describe("the four comparisons that were permissive", () => {
  const AT = EXACT;

  function extremum(knownAt: bigint): ConfirmedExtremumOut {
    return {
      extremum_id: "e1",
      extremum_type: "HIGH",
      extremum_time_ns: AT - 1_000_000_000n,
      known_at_ns: knownAt,
      price: "100",
      confirmation_lag_bars: 2,
      prominence_bps: null,
      source_candidate_id: null,
    };
  }

  it("hides a turn that became knowable a hundred nanoseconds too late", () => {
    // As numbers this instant and the cursor were equal, and `<=` admitted it.
    expect(Number(AT + 100n) === Number(AT)).toBe(true);

    const shown = extremumMarkers({
      confirmed: [extremum(AT + 100n)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: AT,
    });

    expect(shown).toEqual([]);
  });

  it("still shows one knowable exactly at the cursor", () => {
    const shown = extremumMarkers({
      confirmed: [extremum(AT)],
      candidates: [],
      mode: AS_SEEN_THEN,
      atNs: AT,
    });

    expect(shown).toHaveLength(1);
  });

  it("keeps two feature points a hundred nanoseconds apart", () => {
    const points: FeaturePointOut[] = [
      { at_ns: AT, values: { cvd: 1 } },
      { at_ns: AT + 100n, values: { cvd: 2 } },
    ];

    const series = paneSeries(points, "cvd");

    // As numbers these were one key and the second silently replaced the first,
    // under a rule written for a correction.
    expect(series.points).toHaveLength(2);
    expect(series.points.map((p) => p.value)).toEqual([1, 2]);
  });

  it("catches a stop anchored a hundred nanoseconds after the decision", () => {
    const position: PositionOut = {
      position_id: "p1",
      side: "LONG",
      entry_time_ns: AT - 60_000_000_000n,
      average_entry_price: "100",
      initial_stop_price: "90",
      hard_stop_price: null,
      current_strategy_stop: "95",
    };
    const proposals: StopProposalOut[] = [
      {
        at_ns: AT,
        price: "95",
        phase: "trail",
        reasons: ["structure"],
        anchor: {
          kind: "swing",
          price: "94",
          // A hundred nanoseconds after the decision it supposedly informed.
          known_at_ns: AT + 100n,
          description: "a low",
        },
        moved: true,
        refused: false,
      },
    ];

    const view = stopPath({
      position,
      proposals,
      excursion: { mfe_r: 1, mae_r: 0 },
      mode: AS_SEEN_THEN,
      atNs: AT,
    });

    expect(view.state).toBe("inconsistent");
    expect(view.note).toMatch(/after the decision was made/);
  });
});
