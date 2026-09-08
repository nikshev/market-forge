// @trace: REQ-WP-012
import { describe, expect, it } from "vitest";

import { profileBars } from "../volumeProfile";
import type { Profile } from "../volumeProfile";

const PROFILE: Profile = {
  bins: [
    { low: 98, high: 99, volume: 1 },
    { low: 99, high: 100, volume: 2 },
    { low: 100, high: 101, volume: 20 },
    { low: 101, high: 102, volume: 2 },
  ],
  pocIndex: 2,
  valueAreaIndices: [1, 2, 3],
};

describe("volume profile bars", () => {
  it("scales bar widths against the busiest bin", () => {
    const bars = profileBars(PROFILE);

    expect(bars.map((b) => b.width)).toEqual([0.05, 0.1, 1, 0.1]);
  });

  it("marks the POC and the value area distinguishably", () => {
    // Three roles, not two: a reader needs to tell the most-agreed price from
    // the range around it, and both from the wings.
    const bars = profileBars(PROFILE);

    expect(bars.map((b) => b.role)).toEqual(["ordinary", "value-area", "poc", "value-area"]);
  });

  it("draws nothing when there is no profile", () => {
    // A zero-width bar per bin would put a ghost of the overlay on the chart,
    // indistinguishable from a genuinely empty session.
    expect(profileBars(null)).toEqual([]);
    expect(profileBars({ bins: [], pocIndex: 0, valueAreaIndices: [] })).toEqual([]);
  });

  it("survives a profile with no volume at all", () => {
    const empty: Profile = {
      bins: [{ low: 100, high: 101, volume: 0 }],
      pocIndex: 0,
      valueAreaIndices: [0],
    };

    expect(profileBars(empty)[0].width).toBe(0);
  });

  it("keeps each bar's own price range", () => {
    // The chart positions bars by price, so losing the range would stack them.
    const bars = profileBars(PROFILE);

    expect(bars[0]).toMatchObject({ low: 98, high: 99 });
    expect(bars[3]).toMatchObject({ low: 101, high: 102 });
  });
});
