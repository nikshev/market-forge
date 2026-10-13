// @trace: REQ-WP-101
//
// A reader scales a chart: the wheel zooms the time axis, a drag on the price axis scales the price, and a double click on
// an axis puts it back on its auto-fit. (The first version of this requirement turned all of that off to stop the page being
// captured by the wheel, and left a chart nobody could scale -- the owner said so the next day.) The library cannot be drawn
// in jsdom, so what is asserted is the options each chart is created with.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const world = vi.hoisted(() => ({ created: [] as Record<string, any>[] }));

vi.mock("lightweight-charts", () => {
  const series = () => ({
    setData: () => undefined,
    setMarkers: () => undefined,
    createPriceLine: () => ({}),
    attachPrimitive: () => undefined,
    detachPrimitive: () => undefined,
  });
  return {
    ColorType: { Solid: "solid" },
    createChart: (_el: unknown, options: Record<string, any>) => {
      world.created.push(options);
      return {
        addCandlestickSeries: series,
        addLineSeries: series,
        addHistogramSeries: series,
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
  };
});

import { Chart } from "../Chart";
import { CHART_INTERACTION, PLOT_MARGINS } from "../paneChart";
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

describe("what a reader may do to a chart", () => {
  it("zooms the time axis with the mouse wheel, and does not also scroll it", () => {
    expect(CHART_INTERACTION.handleScale.mouseWheel).toBe(true);
    expect(CHART_INTERACTION.handleScroll.mouseWheel).toBe(false);
  });

  it("scales the price axis by dragging it, and resets either axis with a double click", () => {
    expect(CHART_INTERACTION.handleScale.axisPressedMouseMove.price).toBe(true);
    expect(CHART_INTERACTION.handleScale.axisPressedMouseMove.time).toBe(true);
    expect(CHART_INTERACTION.handleScale.axisDoubleClickReset.price).toBe(true);
    expect(CHART_INTERACTION.handleScale.axisDoubleClickReset.time).toBe(true);
  });

  it("keeps pinch and dragging the plot, and leaves a vertical touch to scroll the page", () => {
    expect(CHART_INTERACTION.handleScale.pinch).toBe(true);
    expect(CHART_INTERACTION.handleScroll.pressedMouseMove).toBe(true);
    expect(CHART_INTERACTION.handleScroll.vertTouchDrag).toBe(false);
  });

  it("is what the main chart is created with, with margins that let the candles fill the plot", () => {
    world.created.length = 0;
    render(<Chart bars={BARS} channel={null} signal={null} profile={null} />);

    const options = world.created[0]!;
    expect(options.handleScale).toEqual(CHART_INTERACTION.handleScale);
    expect(options.handleScroll).toEqual(CHART_INTERACTION.handleScroll);
    expect(options.rightPriceScale.scaleMargins).toEqual(PLOT_MARGINS);
    expect(PLOT_MARGINS.top).toBeLessThanOrEqual(0.1);
    expect(PLOT_MARGINS.bottom).toBeLessThanOrEqual(0.1);
  });

  it("is what a pane under it is created with", () => {
    world.created.length = 0;
    render(<PaneChart bars={BARS} feature="cvd_base" points={[]} chart={handle()} title="CVD" scheme="light" />);

    const options = world.created[0]!;
    expect(options.handleScale).toEqual(CHART_INTERACTION.handleScale);
    expect(options.handleScroll).toEqual(CHART_INTERACTION.handleScroll);
  });
});
