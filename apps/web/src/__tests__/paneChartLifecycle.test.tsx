// @trace: REQ-WP-092

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const world = vi.hoisted(() => ({ charts: [] as { series: { removed: boolean; kind: string }[]; removed: boolean; throwOnRemoveSeries: boolean }[] }));

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  createChart: () => {
    const chart = {
      series: [] as { removed: boolean; kind: string }[],
      removed: false,
      throwOnRemoveSeries: false,
      addLineSeries() {
        const s = { removed: false, kind: "line", setData: () => undefined, createPriceLine: () => ({}) };
        chart.series.push(s);
        return s;
      },
      addHistogramSeries() {
        const s = { removed: false, kind: "histogram", setData: () => undefined, createPriceLine: () => ({}) };
        chart.series.push(s);
        return s;
      },
      removeSeries(s: { removed: boolean }) {
        if (chart.removed) {
          throw new Error("chart is disposed");
        }
        s.removed = true;
      },
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
      remove() {
        chart.removed = true;
      },
    };
    world.charts.push(chart);
    return chart;
  },
}));

import { PaneChart } from "../PaneChart";

const STEP = 60_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "1",
  is_final: true,
});
const BARS = [bar(0), bar(1), bar(2)];

function handle() {
  const api = {
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
  };
  return { api: api as never, candles: () => null };
}

describe("the pane chart's lifetime", () => {
  it("names itself for assistive technology as the SVG did", () => {
    render(<PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);

    expect(screen.getByRole("img", { name: "volume over 3 point(s)" })).toBeInTheDocument();
  });

  it("replaces its series when the data changes instead of piling them up", () => {
    world.charts.length = 0;
    const { rerender } = render(
      <PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />,
    );
    const chart = world.charts[0]!;
    const first = [...chart.series];

    rerender(<PaneChart chart={handle()} bars={[...BARS]} feature="volume" points={[]} title="Volume" scheme="light" />);

    expect(first.every((s) => s.removed)).toBe(true);
    expect(chart.series.filter((s) => !s.removed)).toHaveLength(first.length);
  });

  it("makes a new chart for a new scheme and removes the old one", () => {
    world.charts.length = 0;
    const { rerender } = render(
      <PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />,
    );

    rerender(<PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="dark" />);

    expect(world.charts).toHaveLength(2);
    expect(world.charts[0]?.removed).toBe(true);
    expect(world.charts[1]?.removed).toBe(false);
  });

  it("does not throw when it is unmounted after its chart was removed first", () => {
    world.charts.length = 0;
    const { unmount } = render(
      <PaneChart chart={handle()} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />,
    );

    expect(() => unmount()).not.toThrow();
  });
});
