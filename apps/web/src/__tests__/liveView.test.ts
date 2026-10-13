// @trace: REQ-WP-108
//
// Where a chart opens, and whether it follows the newest bar (REQ-WP-108). On 2026-10-13 the owner compared the chart with Investing's: the
// price moves on the last bar there, and here it did not -- the last bar was a few pixels wide under the volume profile, the visible range
// ended at the last *stored* bar so the live bars beyond it were off the right edge, and the price axis spanned the whole history.

import { describe, expect, it } from "vitest";

import { PROFILE_ROOM, RECENT_BARS, followsLatest, recentRange, shiftedRange } from "../series";

describe("recentRange", () => {
  it("opens on the newest bars, not the whole history, so the last bar is wide enough to see move", () => {
    const range = recentRange(500, PROFILE_ROOM)!;

    expect(range.from).toBe(500 - RECENT_BARS);
    expect(RECENT_BARS).toBeLessThanOrEqual(200);
  });

  it("leaves room on the right so the newest bar sits clear of the volume profile, which covers a quarter of the plot", () => {
    const { from, to } = recentRange(500, PROFILE_ROOM)!;
    const newestAt = (499 - from) / (to - from);

    expect(newestAt).toBeLessThan(0.75);
    expect(newestAt).toBeGreaterThan(0.6);
  });

  it("leaves little room when there is no profile to clear", () => {
    const { from, to } = recentRange(500, 0.05)!;

    expect((499 - from) / (to - from)).toBeGreaterThan(0.9);
  });

  it("shows everything there is when there are fewer bars than a screen", () => {
    const { from } = recentRange(40, PROFILE_ROOM)!;

    expect(from).toBe(0);
  });

  it("is nothing for no bars", () => {
    expect(recentRange(0, PROFILE_ROOM)).toBeNull();
  });
});

describe("followsLatest", () => {
  it("is true when the reader is looking at the newest bar", () => {
    expect(followsLatest({ from: 350, to: 560 }, 499)).toBe(true);
    expect(followsLatest({ from: 350, to: 499 }, 499)).toBe(true);
  });

  it("is false once the reader has scrolled back to look at history", () => {
    expect(followsLatest({ from: 100, to: 250 }, 499)).toBe(false);
  });

  it("is false when there is no range yet", () => {
    expect(followsLatest(null, 499)).toBe(false);
  });
});

describe("shiftedRange", () => {
  it("moves both ends by the bars that arrived, so the newest stays where it was on screen", () => {
    expect(shiftedRange({ from: 350, to: 560 }, 16)).toEqual({ from: 366, to: 576 });
  });
});
