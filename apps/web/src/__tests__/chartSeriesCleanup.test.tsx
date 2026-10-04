// @trace: REQ-WP-083
//
// Found by looking at a screenshot, not by any test: every price-axis label appeared twice ("upper upper",
// "center center"), and a third copy of one. The chart's drawing effect ran again on every change of its data
// (bars arrive, then the channel, then the extrema) and added a new candlestick series and new line series each
// time **without removing the old ones**, so the chart carried copies of its own candles, lines and markers.
//
// jsdom cannot draw, so the library is replaced by a fake that records which series are alive.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut, ChannelOut } from "../types";

const world = vi.hoisted(() => ({ series: [] as { kind: string; removed: boolean }[] }));

vi.mock("lightweight-charts", () => {
  const make = (kind: string) => {
    const series = {
      kind,
      removed: false,
      setData: () => undefined,
      setMarkers: () => undefined,
      createPriceLine: () => ({}),
    };
    world.series.push(series);
    return series;
  };
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: () => make("candles"),
      addLineSeries: () => make("line"),
      removeSeries: (series: { removed: boolean }) => {
        series.removed = true;
      },
      timeScale: () => ({ fitContent: () => undefined, setVisibleLogicalRange: () => undefined }),
      remove: () => undefined,
    }),
  };
});

import { Chart } from "../Chart";

const STEP = 900_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;

function bar(i: number): BarOut {
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
}

const BARS = Array.from({ length: 12 }, (_, i) => bar(i));
const CHANNEL: ChannelOut = {
  as_of_ns: BASE + 12n * STEP,
  model_name: "rolling_ols_log_price",
  model_version: "1.0.0",
  lookback: 5,
  center_now: 100,
  upper_now: 102,
  lower_now: 99,
  slope_normalized: 0.5,
  slope_log_per_bar: 0.01,
  width_pct: 3,
  quality_score: 0.8,
  source_max_event_time_ns: BASE + 12n * STEP,
  mode: "AS-SEEN-THEN",
};

const alive = (kind: string): number =>
  world.series.filter((s) => s.kind === kind && !s.removed).length;

describe("the chart does not pile up series as its data changes", () => {
  it("one candlestick series and one line per channel line, however often the data changes", () => {
    world.series.length = 0;
    const props = { signal: null, mode: "AS-SEEN-THEN" as const };
    const { rerender } = render(<Chart bars={BARS} channel={CHANNEL} {...props} />);
    const candles = alive("candles");
    const lines = alive("line");
    expect(candles).toBe(1);
    expect(lines).toBe(3);

    // Each of these is what happens in the page as the extrema and the channel arrive.
    rerender(<Chart bars={[...BARS]} channel={CHANNEL} {...props} />);
    rerender(<Chart bars={[...BARS]} channel={{ ...CHANNEL }} {...props} />);
    rerender(
      <Chart
        bars={[...BARS]}
        channel={{ ...CHANNEL }}
        extrema={{ confirmed: [], candidates: [] }}
        {...props}
      />,
    );

    expect(alive("candles")).toBe(candles);
    expect(alive("line")).toBe(lines);
  });

  it("removes the series it replaces", () => {
    world.series.length = 0;
    const props = { signal: null, mode: "AS-SEEN-THEN" as const };
    const { rerender } = render(<Chart bars={BARS} channel={CHANNEL} {...props} />);

    rerender(<Chart bars={[...BARS]} channel={{ ...CHANNEL }} {...props} />);

    expect(world.series.filter((s) => s.removed).length).toBe(4);
  });

  it("does not throw when the page goes away and the chart is removed first", () => {
    world.series.length = 0;
    const { unmount } = render(<Chart bars={BARS} channel={CHANNEL} signal={null} />);

    expect(() => unmount()).not.toThrow();
  });
});
