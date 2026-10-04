// @trace: REQ-WP-092
//
// The main chart hands out what a pane under it needs to line up with it, and holds the whole sequence of bar
// times whatever layers are on: otherwise the index alignment would depend on a layer.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const world = vi.hoisted(() => ({
  series: [] as { kind: string; data: unknown[]; removed: boolean }[],
  chart: null as null | { options: Record<string, unknown> },
}));

vi.mock("lightweight-charts", () => {
  const make = (kind: string) => {
    const series = {
      kind,
      data: [] as unknown[],
      removed: false,
      setData(d: unknown[]) {
        series.data = d;
      },
      setMarkers: () => undefined,
      createPriceLine: () => ({}),
    };
    world.series.push(series);
    return series;
  };
  return {
    ColorType: { Solid: "solid" },
    createChart: (_el: unknown, options: Record<string, unknown>) => {
      world.chart = { options };
      return {
        addCandlestickSeries: () => make("candles"),
        addLineSeries: () => make("line"),
        removeSeries: (s: { removed: boolean }) => {
          s.removed = true;
        },
        timeScale: () => ({ fitContent: () => undefined, setVisibleLogicalRange: () => undefined }),
        remove: () => undefined,
      };
    },
  };
});

import { Chart } from "../Chart";

const STEP = 900_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number): BarOut => {
  const open = BASE + BigInt(i) * STEP;
  return {
    open_time_ns: open,
    close_time_ns: open + STEP,
    open: "100",
    high: "101",
    low: "99",
    close: "100",
    volume_base: "1",
    is_final: true,
  };
};
const BARS = Array.from({ length: 5 }, (_, i) => bar(i));

describe("the main chart's handle", () => {
  it("hands out the chart and a way to read its current candle series, and clears it on unmount", () => {
    world.series.length = 0;
    const onReady = vi.fn();

    const { unmount } = render(<Chart bars={BARS} channel={null} signal={null} onReady={onReady} />);

    const handle = onReady.mock.calls[0]?.[0];
    expect(handle).toBeTruthy();
    expect(handle.candles()).toBe(world.series.find((s) => s.kind === "candles"));

    unmount();
    expect(onReady).toHaveBeenLastCalledWith(null);
  });

  it("changes nothing when no handle is asked for", () => {
    world.series.length = 0;

    expect(() => render(<Chart bars={BARS} channel={null} signal={null} />)).not.toThrow();
    expect(world.series.filter((s) => s.kind === "candles")).toHaveLength(1);
  });

  it("gives its price scale the minimum width the pane uses", async () => {
    const { PRICE_SCALE_WIDTH } = await import("../paneChart");

    render(<Chart bars={BARS} channel={null} signal={null} />);

    expect((world.chart?.options["rightPriceScale"] as { minimumWidth: number }).minimumWidth).toBe(PRICE_SCALE_WIDTH);
  });

  it("still holds every bar time, as whitespace, when the candles layer is off", () => {
    world.series.length = 0;

    render(<Chart bars={BARS} channel={null} signal={null} overlays={["channel_center"]} />);

    const candles = world.series.find((s) => s.kind === "candles");
    expect(candles?.data).toHaveLength(5);
    expect((candles?.data as { open?: number }[]).every((p) => p.open === undefined)).toBe(true);
  });

  it("holds the candles themselves when the layer is on", () => {
    world.series.length = 0;

    render(<Chart bars={BARS} channel={null} signal={null} />);

    const candles = world.series.find((s) => s.kind === "candles");
    expect((candles?.data as { open?: number }[]).every((p) => p.open === 100)).toBe(true);
  });
});
