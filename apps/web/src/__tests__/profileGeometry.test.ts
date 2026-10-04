// @trace: REQ-WP-089
//
// The volume profile at the side of the chart, on the chart's own price levels. The geometry is decided here, in pure
// functions, so it can be tested without a canvas: each bin is a horizontal bar at its price range, anchored at the right
// edge of the plot, as long as its volume (the busiest at most a quarter of the width), split into unknown, sell and buy.

import { describe, expect, it } from "vitest";

import { coverageLine, formatDuration, profileGeometry } from "../profileView";
import type { VolumeProfileOut } from "../types";

function bin(low: number, buy: number, sell: number, unknown = 0) {
  return {
    low: String(low),
    high: String(low + 10),
    buy: String(buy),
    sell: String(sell),
    unknown: String(unknown),
    trades: 1,
  };
}

function profile(extras: Partial<VolumeProfileOut> = {}): VolumeProfileOut {
  return {
    venue: "binance",
    symbol: "BTCUSDT",
    window: "24h",
    window_ns: 86_400_000_000_000,
    as_of_ns: 1_788_838_800_000_000_000n,
    covers_from_ns: 1_788_830_000_000_000_000n,
    covered_ns: 12_000_000_000_000,
    complete: false,
    bin_width: "10",
    left_out_rows: 0,
    bins: [bin(100, 2, 2), bin(110, 6, 2, 2), bin(120, 1, 1), bin(130, 1, 0)],
    poc_index: 1,
    poc_tie: false,
    value_area_low: "100",
    value_area_high: "140",
    value_area_is_whole_profile: false,
    ...extras,
  };
}

// Higher price, smaller y: the chart's own mapping.
const toY = (price: number): number | null => 600 - price;
const plot = { plotWidth: 800, plotHeight: 600, maxFraction: 0.25, priceToCoordinate: toY };

describe("the geometry of the profile", () => {
  it("puts each bin at its own price range, on the chart's scale", () => {
    const rects = profileGeometry(profile(), plot);

    const second = rects.find((r) => r.low === 110)!;
    expect(second.y).toBe(toY(120));
    expect(second.height).toBe(toY(110)! - toY(120)!);
  });

  it("makes the busiest bin a quarter of the plot's width and the others proportional", () => {
    const rects = profileGeometry(profile(), plot);

    const total = (r: (typeof rects)[number]) => r.unknownWidth + r.sellWidth + r.buyWidth;
    expect(total(rects.find((r) => r.low === 110)!)).toBeCloseTo(200, 6);
    expect(total(rects.find((r) => r.low === 100)!)).toBeCloseTo(80, 6);
    expect(total(rects.find((r) => r.low === 130)!)).toBeCloseTo(20, 6);
  });

  it("splits a bar into unknown, sell and buy, ending at the right edge", () => {
    const rects = profileGeometry(profile(), plot);
    const r = rects.find((x) => x.low === 110)!;

    // volumes 2 unknown, 2 sell, 6 buy of 10: 200 px -> 40, 40, 120
    expect(r.unknownWidth).toBeCloseTo(40, 6);
    expect(r.sellWidth).toBeCloseTo(40, 6);
    expect(r.buyWidth).toBeCloseTo(120, 6);
    expect(r.x).toBeCloseTo(800 - 200, 6);
    expect(r.x + r.unknownWidth + r.sellWidth + r.buyWidth).toBeCloseTo(800, 6);
  });

  it("marks the point of control and the bins inside the value area", () => {
    const rects = profileGeometry(
      profile({ value_area_low: "110", value_area_high: "140" }),
      plot,
    );

    expect(rects.find((r) => r.low === 110)!.isPoc).toBe(true);
    expect(rects.filter((r) => r.isPoc)).toHaveLength(1);
    expect(rects.map((r) => [r.low, r.inValueArea])).toEqual([
      [100, false],
      [110, true],
      [120, true],
      [130, true],
    ]);
  });

  it("leaves out a bin with no coordinate and one wholly outside the plot", () => {
    const rects = profileGeometry(profile(), {
      ...plot,
      priceToCoordinate: (price) => (price === 120 || price === 130 ? null : price === 110 ? 700 : toY(price)),
    });

    // only bins with both edges mapped and some part inside the plot remain
    expect(rects.every((r) => r.y + r.height >= 0 && r.y <= 600)).toBe(true);
    expect(rects.find((r) => r.low === 120)).toBeUndefined();
  });

  it("draws nothing for a profile with no bins or no volume", () => {
    expect(profileGeometry(profile({ bins: [] }), plot)).toEqual([]);
    expect(profileGeometry(profile({ bins: [bin(100, 0, 0)] }), plot)).toEqual([]);
  });
});

describe("the words for a profile", () => {
  it("formats a duration in the largest units that read well", () => {
    expect(formatDuration(0)).toBe("0 m");
    expect(formatDuration(45 * 60_000_000_000)).toBe("45 m");
    expect(formatDuration(200 * 60_000_000_000)).toBe("3 h 20 m");
    expect(formatDuration(26 * 3_600_000_000_000)).toBe("1 d 2 h");
    expect(formatDuration(3_600_000_000_000)).toBe("1 h");
  });

  it("says how much of its window the data covers, never the whole window when it does not", () => {
    expect(coverageLine(profile({ covered_ns: 200 * 60_000_000_000 }))).toBe("covers 3 h 20 m of 24 h");
    expect(coverageLine(profile({ complete: true, covered_ns: 86_400_000_000_000 }))).toBe("24 h window, complete");
    expect(coverageLine(profile({ window: "7d", covered_ns: 90 * 60_000_000_000 }))).toBe("covers 1 h 30 m of 7 d");
  });
});
