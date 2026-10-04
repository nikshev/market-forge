// @trace: REQ-WP-089
//
// The series primitive that draws the profile on the chart's canvas, with a fake series and a fake canvas target: what is
// asserted is what it draws, where, and that it follows the series' own price scale (it asks the series for each edge).

import { describe, expect, it, vi } from "vitest";

import { BUY_COLOUR, ProfilePrimitive, SELL_COLOUR, UNKNOWN_COLOUR } from "../profilePrimitive";
import type { VolumeProfileOut } from "../types";

const profile: VolumeProfileOut = {
  venue: "binance",
  symbol: "BTCUSDT",
  window: "24h",
  window_ns: 86_400_000_000_000,
  as_of_ns: 1n,
  covers_from_ns: 0n,
  covered_ns: 1,
  complete: false,
  bin_width: "10",
  left_out_rows: 0,
  bins: [
    { low: "100", high: "110", buy: "6", sell: "2", unknown: "2", trades: 3 },
    { low: "110", high: "120", buy: "1", sell: "1", unknown: "0", trades: 2 },
  ],
  poc_index: 0,
  poc_tie: false,
  value_area_low: "100",
  value_area_high: "120",
  value_area_is_whole_profile: true,
};

function fakeContext() {
  const calls: { fn: string; args: unknown[]; fill: unknown }[] = [];
  const ctx = {
    fillStyle: "" as unknown,
    strokeStyle: "" as unknown,
    lineWidth: 0,
    fillRect: (...args: unknown[]) => calls.push({ fn: "fillRect", args, fill: ctx.fillStyle }),
    strokeRect: (...args: unknown[]) => calls.push({ fn: "strokeRect", args, fill: ctx.strokeStyle }),
    save: () => undefined,
    restore: () => undefined,
  };
  return { ctx, calls };
}

function attach(primitive: ProfilePrimitive, priceToCoordinate: (p: number) => number | null) {
  const requestUpdate = vi.fn();
  primitive.attached?.({
    series: { priceToCoordinate } as never,
    chart: {} as never,
    requestUpdate,
  });
  return requestUpdate;
}

function render(primitive: ProfilePrimitive, width = 800, height = 600) {
  const { ctx, calls } = fakeContext();
  const view = primitive.paneViews()[0]!;
  view.renderer()?.draw({
    useMediaCoordinateSpace: (f: (scope: unknown) => unknown) =>
      f({ context: ctx, mediaSize: { width, height } }),
  } as never);
  return calls;
}

describe("the profile primitive", () => {
  it("asks the series for each bin's price edges and draws a rectangle per part, in the buy, sell and unknown colours", () => {
    const primitive = new ProfilePrimitive(profile);
    const asked: number[] = [];
    attach(primitive, (price) => {
      asked.push(price);
      return 600 - price;
    });

    const calls = render(primitive);

    expect(new Set(asked)).toEqual(new Set([100, 110, 120]));
    const fills = calls.filter((c) => c.fn === "fillRect").map((c) => c.fill);
    expect(fills.filter((f) => f === BUY_COLOUR).length).toBe(2);
    expect(fills.filter((f) => f === SELL_COLOUR).length).toBe(2);
    expect(fills.filter((f) => f === UNKNOWN_COLOUR).length).toBe(1);
  });

  it("draws the busiest bin a quarter of the plot wide, flush with the right edge", () => {
    const primitive = new ProfilePrimitive(profile);
    attach(primitive, (price) => 600 - price);

    const calls = render(primitive, 1000, 600).filter((c) => c.fn === "fillRect");

    const rights = calls.map((c) => (c.args[0] as number) + (c.args[2] as number));
    expect(Math.max(...rights)).toBeCloseTo(1000, 6);
    const widest = Math.min(...calls.map((c) => c.args[0] as number));
    expect(widest).toBeCloseTo(1000 - 250, 6);
  });

  it("outlines the point of control", () => {
    const primitive = new ProfilePrimitive(profile);
    attach(primitive, (price) => 600 - price);

    const outlines = render(primitive).filter((c) => c.fn === "strokeRect");

    expect(outlines).toHaveLength(1);
  });

  it("draws nothing with no profile, and asks for a redraw when a profile arrives", () => {
    const primitive = new ProfilePrimitive(null);
    const requestUpdate = attach(primitive, (price) => 600 - price);
    expect(render(primitive)).toEqual([]);

    primitive.setProfile(profile);

    expect(requestUpdate).toHaveBeenCalled();
    expect(render(primitive).length).toBeGreaterThan(0);
  });

  it("draws nothing when it is not attached to a series", () => {
    expect(render(new ProfilePrimitive(profile))).toEqual([]);
  });
});
