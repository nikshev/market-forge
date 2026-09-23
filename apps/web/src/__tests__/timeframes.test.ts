// @trace: REQ-WP-074
//
// The one place the frontend matches a link's token against what the
// deployment reported. It carries no table of its own: durations come from the
// API, and a token that is not in the offered set is not quietly folded into
// one that is.

import { describe, expect, it } from "vitest";

import { DEFAULT_TIMEFRAME, matchTimeframe, type TimeframeOption } from "../timeframes";

const OFFERED: TimeframeOption[] = [
  { token: "1m", timeframeNs: 60_000_000_000 },
  { token: "5m", timeframeNs: 300_000_000_000 },
  { token: "15m", timeframeNs: 900_000_000_000 },
  { token: "1h", timeframeNs: 3_600_000_000_000 },
];

describe("the default timeframe", () => {
  it("is a real token, spelled once", () => {
    expect(DEFAULT_TIMEFRAME).toBe("15m");
  });

  it("is offered by the default deployment", () => {
    // The assumption the spec records: a deployment that configured the default
    // away would refuse it like any other token, but the shipped configuration
    // must not do that.
    expect(matchTimeframe(OFFERED, DEFAULT_TIMEFRAME)).not.toBeNull();
  });
});

describe("matching a token against the offered set", () => {
  it("returns the option, duration included", () => {
    expect(matchTimeframe(OFFERED, "1h")).toEqual({
      token: "1h",
      timeframeNs: 3_600_000_000_000,
    });
  });

  it("is exact: no case folding, no trimming, no aliases", () => {
    for (const token of ["1H", "15m ", " 15m", "15M", "60m", "0.25h"]) {
      expect(matchTimeframe(OFFERED, token)).toBeNull();
    }
  });

  it("returns null for a token that is simply absent", () => {
    expect(matchTimeframe(OFFERED, "7m")).toBeNull();
    expect(matchTimeframe(OFFERED, "1M")).toBeNull();
    expect(matchTimeframe(OFFERED, "1w")).toBeNull();
  });

  it("returns null for an empty set", () => {
    expect(matchTimeframe([], "15m")).toBeNull();
  });
});
