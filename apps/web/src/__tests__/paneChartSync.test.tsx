// @trace: REQ-WP-092
//
// The pane chart with the library replaced by a fake that records what it is asked. jsdom cannot lay a chart
// out; what can be asserted is the data handed to the library and the synchronisation wiring.

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BarOut, FeaturePointOut } from "../types";

type Fake = ReturnType<typeof makeFakeChart>;

const world = vi.hoisted(() => ({ charts: [] as unknown[] }));

function makeFakeChart(options: Record<string, unknown> = {}) {
  const series: { kind: string; data: unknown[]; options: Record<string, unknown>; lines: unknown[]; removed: boolean }[] = [];
  const rangeHandlers: ((range: { from: number; to: number } | null) => void)[] = [];
  const crosshairHandlers: ((param: { time?: number }) => void)[] = [];
  let range: { from: number; to: number } | null = null;
  const chart = {
    options,
    series,
    rangeHandlers,
    crosshairHandlers,
    removed: false,
    setCalls: [] as { from: number; to: number }[],
    crosshairSet: [] as unknown[][],
    crosshairCleared: 0,
    make(kind: string, opts: Record<string, unknown>) {
      const s = {
        kind,
        data: [] as unknown[],
        options: opts,
        lines: [] as unknown[],
        removed: false,
        setData(d: unknown[]) {
          s.data = d;
        },
        createPriceLine(line: unknown) {
          s.lines.push(line);
          return {};
        },
      };
      series.push(s);
      return s;
    },
    addLineSeries(opts: Record<string, unknown> = {}) {
      return chart.make("line", opts);
    },
    addHistogramSeries(opts: Record<string, unknown> = {}) {
      return chart.make("histogram", opts);
    },
    removeSeries(s: { removed: boolean }) {
      s.removed = true;
    },
    applyOptions: vi.fn(),
    subscribeCrosshairMove(h: (param: { time?: number }) => void) {
      crosshairHandlers.push(h);
    },
    unsubscribeCrosshairMove(h: (param: { time?: number }) => void) {
      crosshairHandlers.splice(crosshairHandlers.indexOf(h), 1);
    },
    setCrosshairPosition(...args: unknown[]) {
      chart.crosshairSet.push(args);
    },
    clearCrosshairPosition() {
      chart.crosshairCleared += 1;
    },
    timeScale: () => ({
      subscribeVisibleLogicalRangeChange(h: (r: { from: number; to: number } | null) => void) {
        rangeHandlers.push(h);
      },
      unsubscribeVisibleLogicalRangeChange(h: (r: { from: number; to: number } | null) => void) {
        rangeHandlers.splice(rangeHandlers.indexOf(h), 1);
      },
      getVisibleLogicalRange: () => range,
      setVisibleLogicalRange(r: { from: number; to: number }) {
        chart.setCalls.push(r);
        range = r;
        for (const h of [...rangeHandlers]) {
          h(r);
        }
      },
      fitContent: () => undefined,
    }),
    remove() {
      chart.removed = true;
    },
  };
  return chart;
}

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  createChart: (_el: unknown, options: Record<string, unknown>) => {
    const chart = makeFakeChart(options);
    world.charts.push(chart);
    return chart;
  },
}));

import { PaneChart } from "../PaneChart";

const STEP = 60_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number, extras: Partial<BarOut> = {}): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: String(i + 1),
  is_final: true,
  ...extras,
});
const BARS = Array.from({ length: 6 }, (_, i) => bar(i));
const secs = (i: number): number => Number((BASE + BigInt(i + 1) * STEP) / 1_000_000_000n);
const feature = (i: number, values: Record<string, number>): FeaturePointOut => ({
  at_ns: BASE + BigInt(i + 1) * STEP,
  values,
});

function mainHandle() {
  const api = makeFakeChart();
  const candles = { kind: "candles" };
  return { api, handle: { api: api as never, candles: () => candles as never } };
}
const pane = (): Fake => world.charts.at(-1) as Fake;

beforeEach(() => {
  world.charts.length = 0;
});

describe("the data handed to the library", () => {
  it("holds every bar time in a whitespace backbone, so the pane's axis is the chart's", () => {
    const { handle } = mainHandle();

    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);

    const backbone = pane().series.find((s) => s.kind === "line");
    expect(backbone?.data).toEqual(BARS.map((_, i) => ({ time: secs(i) })));
  });

  it("draws volume as a histogram, coloured by direction, at the candles' times", () => {
    const { handle } = mainHandle();
    const bars = [bar(0, { open: "100", close: "102" }), bar(1, { open: "102", close: "101" })];

    render(<PaneChart chart={handle} bars={bars} feature="volume" points={[]} title="Volume" scheme="light" />);

    const histogram = pane().series.find((s) => s.kind === "histogram");
    expect(histogram?.data).toEqual([
      { time: secs(0), value: 1, color: "#26a69a" },
      { time: secs(1), value: 2, color: "#ef5350" },
    ]);
  });

  it("draws CVD as one line series per run, with a zero line, and never joins two runs", () => {
    const { handle } = mainHandle();
    const points = [
      feature(0, { cvd_base: 1, cvd_run: 0 }),
      feature(1, { cvd_base: 3, cvd_run: 0 }),
      feature(3, { cvd_base: -2, cvd_run: 1 }),
      feature(4, { cvd_base: 0, cvd_run: 1 }),
    ];

    render(<PaneChart chart={handle} bars={BARS} feature="cvd_base" points={points} title="CVD (base)" scheme="light" />);

    const lines = pane().series.filter((s) => s.kind === "line").slice(1);
    expect(lines).toHaveLength(2);
    expect(lines[0]?.data).toEqual([
      { time: secs(0), value: 1 },
      { time: secs(1), value: 3 },
    ]);
    expect(lines[1]?.data).toEqual([
      { time: secs(3), value: -2 },
      { time: secs(4), value: 0 },
    ]);
    expect(lines.some((s) => s.lines.some((l) => (l as { price: number }).price === 0))).toBe(true);
  });

  it("draws any other feature as one line over the aligned bars, with a gap where a bar has none", () => {
    const { handle } = mainHandle();
    const points = [feature(0, { ofi_1m: 1 }), feature(2, { ofi_1m: 4 })];

    render(<PaneChart chart={handle} bars={BARS} feature="ofi_1m" points={points} title="OFI (1m)" scheme="light" />);

    const line = pane().series.filter((s) => s.kind === "line")[1];
    expect(line?.data).toHaveLength(6);
    expect((line?.data as { value?: number }[])[1]?.value).toBeUndefined();
    expect((line?.data as { value?: number }[])[2]?.value).toBe(4);
  });
});

describe("how the two charts are made to agree", () => {
  it("gives the pane the same price-scale minimum width the main chart uses", async () => {
    const { handle } = mainHandle();
    const { PRICE_SCALE_WIDTH } = await import("../paneChart");

    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);

    const scale = pane().options["rightPriceScale"] as { minimumWidth: number };
    expect(scale.minimumWidth).toBe(PRICE_SCALE_WIDTH);
  });

  it("takes the main chart's visible range when it is created", () => {
    const { api, handle } = mainHandle();
    api.timeScale().setVisibleLogicalRange({ from: 2, to: 5 });

    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);

    expect(pane().setCalls).toContainEqual({ from: 2, to: 5 });
  });

  it("follows the main chart's range, once, with no echo back", () => {
    const { api, handle } = mainHandle();
    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);
    const before = pane().setCalls.length;
    const mainBefore = api.setCalls.length;

    api.timeScale().setVisibleLogicalRange({ from: 1, to: 4 });

    expect(pane().setCalls.length).toBe(before + 1);
    expect(pane().setCalls.at(-1)).toEqual({ from: 1, to: 4 });
    expect(api.setCalls.length).toBe(mainBefore + 1);
  });

  it("drives the main chart when the reader moves the pane, once, with no echo back", () => {
    const { api, handle } = mainHandle();
    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);
    fireEvent.pointerEnter(screen.getByRole("img"));
    const mainBefore = api.setCalls.length;
    const paneBefore = pane().setCalls.length;

    pane().timeScale().setVisibleLogicalRange({ from: 3, to: 6 });

    expect(api.setCalls.length).toBe(mainBefore + 1);
    expect(api.setCalls.at(-1)).toEqual({ from: 3, to: 6 });
    expect(pane().setCalls.length).toBe(paneBefore + 1);
  });

  it("does not let a range the pane reports by itself move the main chart, and puts the pane back", () => {
    // Replacing a series makes the library reset a pane's range for a moment. That is not the reader's, and
    // sending it to the main chart put the chart on the first bars with an empty left edge (found on the live page).
    const { api, handle } = mainHandle();
    api.timeScale().setVisibleLogicalRange({ from: 379, to: 504 });
    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);
    const mainBefore = api.setCalls.length;

    pane().timeScale().setVisibleLogicalRange({ from: -65, to: 60 });

    expect(api.setCalls.length).toBe(mainBefore);
    expect(pane().setCalls.at(-1)).toEqual({ from: 379, to: 504 });
  });

  it("stops following the reader's pointer when it leaves the pane", () => {
    const { api, handle } = mainHandle();
    api.timeScale().setVisibleLogicalRange({ from: 10, to: 20 });
    render(<PaneChart chart={handle} bars={BARS} feature="volume" points={[]} title="Volume" scheme="light" />);
    fireEvent.pointerEnter(screen.getByRole("img"));
    fireEvent.pointerLeave(screen.getByRole("img"));
    const mainBefore = api.setCalls.length;

    pane().timeScale().setVisibleLogicalRange({ from: 0, to: 5 });

    expect(api.setCalls.length).toBe(mainBefore);
  });

  it("shows the crosshair at the same bar on the other chart, both ways, and clears it with the mouse gone", () => {
    const { api, handle } = mainHandle();
    render(
      <PaneChart chart={handle} bars={BARS} feature="ofi_1m" points={[feature(2, { ofi_1m: 4 })]} title="OFI (1m)" scheme="light" />,
    );

    api.crosshairHandlers.forEach((h) => h({ time: secs(2) }));
    expect(pane().crosshairSet.at(-1)?.[0]).toBe(4);
    expect(pane().crosshairSet.at(-1)?.[1]).toBe(secs(2));

    pane().crosshairHandlers.forEach((h) => h({ time: secs(3) }));
    expect(api.crosshairSet.at(-1)?.[1]).toBe(secs(3));
    expect(api.crosshairSet.at(-1)?.[0]).toBe(100);

    api.crosshairHandlers.forEach((h) => h({}));
    expect(pane().crosshairCleared).toBe(1);
  });
});
