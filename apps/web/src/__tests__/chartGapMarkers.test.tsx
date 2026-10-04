// @trace: REQ-WP-086
//
// The chart carries a marker at each hole in the bars, in the one call the library replaces its whole set with, ordered by
// time, and a mark at the same bar (a signal, an extremum) is not hidden by it.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut, ExtremaResponse } from "../types";

const world = vi.hoisted(() => ({ markerCalls: [] as { time: number; text?: string; id?: string }[][] }));

vi.mock("lightweight-charts", () => {
  const make = () => ({
    setData: () => undefined,
    setMarkers: (marks: { time: number; text?: string; id?: string }[]) => {
      world.markerCalls.push(marks);
    },
    createPriceLine: () => ({}),
  });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: make,
      addLineSeries: make,
      removeSeries: () => undefined,
      timeScale: () => ({ fitContent: () => undefined, setVisibleLogicalRange: () => undefined }),
      remove: () => undefined,
    }),
  };
});

import { Chart } from "../Chart";
import { toSeconds } from "../series";

const STEP = 900_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number, extras: Partial<BarOut> = {}): BarOut => {
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
    ...extras,
  };
};
const bars = (indices: number[]) => indices.map((i) => bar(i));
const last = () => world.markerCalls.at(-1) ?? [];
const gapMarks = (marks: { time: number; text?: string }[]) =>
  marks.filter((m) => m.text?.endsWith(" missing"));

describe("the chart and a hole in the bars", () => {
  it("carries one marker at the first bar after the hole, stating how many are missing", () => {
    world.markerCalls.length = 0;

    render(<Chart bars={bars([0, 1, 2, 6, 7])} channel={null} signal={null} />);

    expect(gapMarks(last())).toHaveLength(1);
    expect(gapMarks(last())[0]?.text).toBe("3 missing");
    expect(gapMarks(last())[0]?.time).toBe(toSeconds(bar(6).close_time_ns));
  });

  it("carries one per hole, and none for contiguous bars", () => {
    world.markerCalls.length = 0;
    render(<Chart bars={bars([0, 2, 3, 7])} channel={null} signal={null} />);
    expect(gapMarks(last())).toHaveLength(2);

    world.markerCalls.length = 0;
    render(<Chart bars={bars([0, 1, 2, 3])} channel={null} signal={null} />);
    expect(gapMarks(last())).toHaveLength(0);
  });

  it("does not mark a bar of zero volume", () => {
    world.markerCalls.length = 0;

    render(<Chart bars={[bar(0), bar(1, { volume_base: "0" }), bar(2)]} channel={null} signal={null} />);

    expect(gapMarks(last())).toHaveLength(0);
  });

  it("keeps every mark in one call, ordered by time, and a gap marker does not hide another at the same bar", () => {
    world.markerCalls.length = 0;
    const extrema: ExtremaResponse = {
      confirmed: [
        {
          extremum_id: "e1",
          extremum_type: "HIGH",
          extremum_time_ns: bar(6).close_time_ns,
          known_at_ns: bar(7).close_time_ns,
          price: "101",
          confirmation_lag_bars: 1,
          prominence_bps: null,
          source_candidate_id: null,
        },
      ],
      candidates: [],
    };

    render(<Chart bars={bars([0, 1, 2, 6, 7])} channel={null} signal={null} extrema={extrema} mode="CURRENT REFIT" />);

    const marks = last();
    expect(marks).toHaveLength(2);
    expect(gapMarks(marks)).toHaveLength(1);
    const times = marks.map((m) => m.time as number);
    expect([...times].sort((a, b) => a - b)).toEqual(times);
    expect(marks.filter((m) => m.time === toSeconds(bar(6).close_time_ns))).toHaveLength(2);
  });

  it("calls setMarkers once per drawing, not once for the gaps and once for the rest", () => {
    world.markerCalls.length = 0;

    render(<Chart bars={bars([0, 1, 2, 6, 7])} channel={null} signal={null} />);

    expect(world.markerCalls).toHaveLength(1);
  });
});
