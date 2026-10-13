// @trace: REQ-WP-102
//
// The live bars on the chart: drawn after the last stored bar, updated without recreating the chart or touching the reader's
// range, superseded by a stored bar for the same minute, and held as whitespace -- so the panes' axis lines up -- when the
// candles layer is off. The panes hold the same bars (the main chart and a pane align by index).

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const world = vi.hoisted(() => ({
  series: [] as { kind: string; data: any[]; sets: number }[],
  fits: 0,
  ranges: 0,
}));

vi.mock("lightweight-charts", () => {
  const make = (kind: string) => {
    const series = {
      kind,
      data: [] as any[],
      sets: 0,
      setData(d: any[]) {
        series.data = d;
        series.sets += 1;
      },
      setMarkers: () => undefined,
      createPriceLine: () => ({}),
      attachPrimitive: () => undefined,
      detachPrimitive: () => undefined,
    };
    world.series.push(series);
    return series;
  };
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: () => make("candles"),
      addLineSeries: () => make("line"),
      addHistogramSeries: () => make("histogram"),
      removeSeries: () => undefined,
      applyOptions: () => undefined,
      subscribeCrosshairMove: () => undefined,
      unsubscribeCrosshairMove: () => undefined,
      setCrosshairPosition: () => undefined,
      clearCrosshairPosition: () => undefined,
      timeScale: () => ({
        fitContent: () => {
          world.fits += 1;
        },
        setVisibleLogicalRange: () => {
          world.ranges += 1;
        },
        subscribeVisibleLogicalRangeChange: () => undefined,
        unsubscribeVisibleLogicalRangeChange: () => undefined,
        getVisibleLogicalRange: () => null,
      }),
      remove: () => undefined,
    }),
  };
});

import { Chart } from "../Chart";
import { PaneChart } from "../PaneChart";

const MIN = 60_000_000_000n;
const T0 = 1_788_800_040_000_000_000n - (1_788_800_040_000_000_000n % MIN);
const bar = (minute: number, over: Partial<BarOut> = {}): BarOut => ({
  open_time_ns: T0 + BigInt(minute) * MIN,
  close_time_ns: T0 + BigInt(minute + 1) * MIN,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "1",
  is_final: true,
  ...over,
});
const secondsOf = (minute: number): number => Number((T0 + BigInt(minute + 1) * MIN) / 1_000_000_000n);

const STORED = [bar(0), bar(1), bar(2)];
const candles = () => world.series.filter((s) => s.kind === "candles").at(-1)!;

describe("the main chart with live bars", () => {
  it("draws the live bars after the last stored one, in time order", () => {
    world.series.length = 0;

    render(<Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3, { close: "105", is_final: false }), bar(4)]} />);

    expect(candles().data.map((p) => p.time)).toEqual([0, 1, 2, 3, 4].map(secondsOf));
    expect(candles().data[3]).toMatchObject({ close: 105, open: 100 });
  });

  it("lets a stored bar supersede the live one for its minute", () => {
    world.series.length = 0;

    render(<Chart bars={STORED} channel={null} signal={null} liveBars={[bar(2, { close: "999" }), bar(3)]} />);

    expect(candles().data).toHaveLength(4);
    expect(candles().data[2]).toMatchObject({ close: 100 });
  });

  it("draws nothing extra when there are no live bars, exactly as before", () => {
    world.series.length = 0;

    render(<Chart bars={STORED} channel={null} signal={null} />);

    expect(candles().data).toHaveLength(3);
  });

  it("holds the live bars as whitespace when the candles layer is off, so the panes line up", () => {
    world.series.length = 0;

    render(<Chart bars={STORED} channel={null} signal={null} overlays={["channel_center"]} liveBars={[bar(3), bar(4)]} />);

    expect(candles().data).toHaveLength(5);
    expect((candles().data as { open?: number }[]).every((p) => p.open === undefined)).toBe(true);
  });

  it("updates the candle in place when a live bar changes: no new series, no new fit of the range", () => {
    world.series.length = 0;
    world.fits = 0;
    world.ranges = 0;
    const { rerender } = render(
      <Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3, { close: "101", is_final: false })]} isInitialLoad={false} />,
    );
    const seriesBefore = world.series.length;
    const series = candles();

    rerender(
      <Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3, { close: "107", is_final: false })]} isInitialLoad={false} />,
    );

    expect(world.series).toHaveLength(seriesBefore);
    expect(candles()).toBe(series);
    expect(series.data.at(-1)).toMatchObject({ close: 107 });
    expect(world.fits).toBe(0);
    expect(world.ranges).toBe(0);
  });

  it("adds a new live minute without recreating the chart's series", () => {
    world.series.length = 0;
    const { rerender } = render(<Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3)]} isInitialLoad={false} />);
    const series = candles();

    rerender(<Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3), bar(4)]} isInitialLoad={false} />);

    expect(series.data).toHaveLength(5);
    expect(candles()).toBe(series);
  });

  it("draws the live bars again after the stored bars are reloaded, and drops the ones the table now has", () => {
    world.series.length = 0;
    const { rerender } = render(<Chart bars={STORED} channel={null} signal={null} liveBars={[bar(3), bar(4)]} isInitialLoad={false} />);

    rerender(<Chart bars={[...STORED, bar(3, { close: "123" })]} channel={null} signal={null} liveBars={[bar(3), bar(4)]} isInitialLoad={false} />);

    expect(candles().data.map((p) => p.time)).toEqual([0, 1, 2, 3, 4].map(secondsOf));
    expect(candles().data[3]).toMatchObject({ close: 123 });
    expect(candles().data).toHaveLength(5);
  });
});

describe("a pane with live bars", () => {
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

  it("holds the same bar times as the chart, so the two axes stay aligned", () => {
    world.series.length = 0;

    render(
      <PaneChart chart={handle()} bars={STORED} liveBars={[bar(3, { is_final: false }), bar(4)]} feature="cvd_base" points={[]} title="CVD" scheme="light" />,
    );

    const spine = world.series.find((s) => s.kind === "line")!;
    expect(spine.data.map((p) => p.time)).toEqual([0, 1, 2, 3, 4].map(secondsOf));
  });

  it("draws a finished live bar's volume and leaves a forming one as whitespace", () => {
    world.series.length = 0;

    render(
      <PaneChart
        chart={handle()}
        bars={STORED}
        liveBars={[bar(3, { volume_base: "7", is_final: true }), bar(4, { volume_base: "9", is_final: false })]}
        feature="volume"
        points={[]}
        title="Volume"
        scheme="light"
      />,
    );

    const histogram = world.series.find((s) => s.kind === "histogram")!;
    expect(histogram.data).toHaveLength(5);
    expect(histogram.data[3]).toMatchObject({ value: 7 });
    expect(histogram.data[4].value).toBeUndefined();
  });

  it("is unchanged with no live bars", () => {
    world.series.length = 0;

    render(<PaneChart chart={handle()} bars={STORED} feature="volume" points={[]} title="Volume" scheme="light" />);

    expect(world.series.find((s) => s.kind === "histogram")!.data).toHaveLength(3);
  });
});
