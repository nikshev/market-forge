// @trace: REQ-WP-101
//
// A chart is read, not operated: scrolling the page with the pointer over it must scroll the page, and the price
// axis must stay on its own auto-fit. lightweight-charts' defaults zoom the time axis on every wheel tick -- which
// stopped the page scrolling over the chart and squeezed and stretched the time axis under a reader who was only
// moving down to the panes -- and let a drag on the price axis switch the auto-fit off for good. The library cannot be
// drawn in jsdom, so what is asserted is the options each chart is created with.

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
import { READING_INTERACTION, PLOT_MARGINS } from "../paneChart";
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
  it("does not zoom or scroll the time axis on the mouse wheel, so the page scrolls over the chart", () => {
    expect(READING_INTERACTION.handleScale.mouseWheel).toBe(false);
    expect(READING_INTERACTION.handleScroll.mouseWheel).toBe(false);
  });

  it("leaves the price axis to its auto-fit: no drag on it, no vertical touch drag", () => {
    expect(READING_INTERACTION.handleScale.axisPressedMouseMove.price).toBe(false);
    expect(READING_INTERACTION.handleScroll.vertTouchDrag).toBe(false);
  });

  it("keeps what a reader does want: pinch, and dragging along the time axis", () => {
    expect(READING_INTERACTION.handleScale.axisPressedMouseMove.time).toBe(true);
    expect(READING_INTERACTION.handleScroll.pressedMouseMove).toBe(true);
  });

  it("is what the main chart is created with, with margins that let the candles fill the plot", () => {
    world.created.length = 0;
    render(<Chart bars={BARS} channel={null} signal={null} profile={null} />);

    const options = world.created[0]!;
    expect(options.handleScale).toEqual(READING_INTERACTION.handleScale);
    expect(options.handleScroll).toEqual(READING_INTERACTION.handleScroll);
    expect(options.rightPriceScale.scaleMargins).toEqual(PLOT_MARGINS);
    expect(PLOT_MARGINS.top).toBeLessThanOrEqual(0.1);
    expect(PLOT_MARGINS.bottom).toBeLessThanOrEqual(0.1);
  });

  it("is what a pane under it is created with", () => {
    world.created.length = 0;
    render(<PaneChart bars={BARS} feature="cvd_base" points={[]} chart={handle()} title="CVD" scheme="light" />);

    const options = world.created[0]!;
    expect(options.handleScale).toEqual(READING_INTERACTION.handleScale);
    expect(options.handleScroll).toEqual(READING_INTERACTION.handleScroll);
  });
});
