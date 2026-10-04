// @trace: REQ-WP-086
//
// The lower pane does not contradict the chart about a hole: its histogram carries the same markers at the bars that have a
// value, and a CVD run is marked when it starts at a gap marker's time -- not when it starts after a trade-id break, where
// nothing is missing from the bars.

import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BarOut, FeaturePointOut } from "../types";

const world = vi.hoisted(() => ({
  series: [] as { kind: string; data: unknown[]; markers: { time: number; text?: string }[] }[],
}));

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  createChart: () => {
    const make = (kind: string) => {
      const s = {
        kind,
        data: [] as unknown[],
        markers: [] as { time: number; text?: string }[],
        setData(d: unknown[]) {
          s.data = d;
        },
        setMarkers(m: { time: number; text?: string }[]) {
          s.markers = m;
        },
        createPriceLine: () => ({}),
      };
      world.series.push(s);
      return s;
    };
    return {
      addLineSeries: () => make("line"),
      addHistogramSeries: () => make("histogram"),
      removeSeries: () => undefined,
      applyOptions: () => undefined,
      subscribeCrosshairMove: () => undefined,
      unsubscribeCrosshairMove: () => undefined,
      setCrosshairPosition: () => undefined,
      clearCrosshairPosition: () => undefined,
      timeScale: () => ({
        subscribeVisibleLogicalRangeChange: () => undefined,
        unsubscribeVisibleLogicalRangeChange: () => undefined,
        getVisibleLogicalRange: () => null,
        setVisibleLogicalRange: () => undefined,
        fitContent: () => undefined,
      }),
      remove: () => undefined,
    };
  },
}));

import { PaneChart } from "../PaneChart";
import { toSeconds } from "../series";

const STEP = 60_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "2",
  is_final: true,
});
// Bars 0,1,2 then a hole of 3 and bars 6,7,8.
const BARS = [0, 1, 2, 6, 7, 8].map(bar);
const feature = (i: number, values: Record<string, number>): FeaturePointOut => ({
  at_ns: BASE + BigInt(i + 1) * STEP,
  values,
});
const handle = () => ({
  api: {
    subscribeCrosshairMove: () => undefined,
    unsubscribeCrosshairMove: () => undefined,
    setCrosshairPosition: () => undefined,
    clearCrosshairPosition: () => undefined,
    timeScale: () => ({
      subscribeVisibleLogicalRangeChange: () => undefined,
      unsubscribeVisibleLogicalRangeChange: () => undefined,
      getVisibleLogicalRange: () => null,
      setVisibleLogicalRange: () => undefined,
    }),
  } as never,
  candles: () => null,
});
const gapTime = toSeconds(bar(6).close_time_ns);

beforeEach(() => {
  world.series.length = 0;
});

describe("gap markers in the lower pane", () => {
  it("puts the chart's marker on the Volume histogram at the first bar after the hole", () => {
    render(<PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);

    const histogram = world.series.find((s) => s.kind === "histogram");
    expect(histogram?.markers).toHaveLength(1);
    expect(histogram?.markers[0]?.time).toBe(gapTime);
  });

  it("marks a CVD run whose first point is at a gap, and not one that starts after a trade-id break", () => {
    const points = [
      feature(0, { cvd_base: 1, cvd_run: 0 }),
      feature(1, { cvd_base: 2, cvd_run: 0 }),
      // run 1 starts at bar 6, right after the hole
      feature(6, { cvd_base: 5, cvd_run: 1 }),
      feature(7, { cvd_base: 6, cvd_run: 1 }),
      // run 2 starts at bar 8 with nothing missing before it: a trade-id break
      feature(8, { cvd_base: 1, cvd_run: 2 }),
    ];

    render(<PaneChart chart={handle()} bars={BARS} feature="cvd_base" points={points} title="CVD (base)" scheme="light" />);

    const runs = world.series.filter((s) => s.kind === "line").slice(1);
    expect(runs).toHaveLength(3);
    expect(runs[0]?.markers).toHaveLength(0);
    expect(runs[1]?.markers.map((m) => m.time)).toEqual([gapTime]);
    expect(runs[2]?.markers).toHaveLength(0);
  });

  it("sets no markers when the bars are contiguous", () => {
    render(
      <PaneChart chart={handle()} bars={[0, 1, 2, 3].map(bar)} feature="volume" points={[]} title="Volume" scheme="light" />,
    );

    expect(world.series.find((s) => s.kind === "histogram")?.markers).toHaveLength(0);
  });
});
