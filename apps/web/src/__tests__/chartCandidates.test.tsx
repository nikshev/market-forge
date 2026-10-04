// @trace: REQ-WP-084
//
// `Chart` is the only production caller of `extremumMarkers`, and `includeCandidates` defaults to `true` there
// so the pure function's older callers keep their meaning. So the thing that must be pinned is that `Chart`
// never relies on that default: with no `showCandidates` it hands the library the confirmed marks alone.
// jsdom cannot draw, so the library is replaced by a fake that records the markers it was given.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut, ExtremaResponse } from "../types";

const world = vi.hoisted(() => ({
  markerCalls: [] as { time: number; text?: string }[][],
  series: [] as { kind: string; removed: boolean }[],
}));

vi.mock("lightweight-charts", () => {
  const make = (kind: string) => {
    const series = {
      kind,
      removed: false,
      setData: () => undefined,
      setMarkers: (marks: { time: number; text?: string }[]) => {
        world.markerCalls.push(marks);
      },
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

const EXTREMA: ExtremaResponse = {
  confirmed: [
    {
      extremum_id: "c1",
      extremum_type: "HIGH",
      extremum_time_ns: BASE + 2n * STEP,
      known_at_ns: BASE + 4n * STEP,
      price: "101",
      confirmation_lag_bars: 2,
      prominence_bps: null,
      source_candidate_id: null,
    },
  ],
  candidates: [
    {
      candidate_id: "k1",
      candidate_type: "LOW",
      candidate_time_ns: BASE + 6n * STEP,
      observed_at_ns: BASE + 7n * STEP,
      price: "99",
      structural_score: 0.4,
    },
    {
      candidate_id: "k2",
      candidate_type: "HIGH",
      candidate_time_ns: BASE + 8n * STEP,
      observed_at_ns: BASE + 9n * STEP,
      price: "101",
      structural_score: 0.3,
    },
  ],
};

const lastMarks = (): { time: number; text?: string }[] =>
  world.markerCalls.at(-1) ?? [];
const candidateMarks = (marks: { text?: string }[]) => marks.filter((m) => m.text === "?");

describe("the chart and candidate extrema", () => {
  it("draws the confirmed turn and no candidate by default", () => {
    world.markerCalls.length = 0;

    render(<Chart bars={BARS} channel={null} signal={null} extrema={EXTREMA} mode="CURRENT REFIT" />);

    expect(lastMarks()).toHaveLength(1);
    expect(candidateMarks(lastMarks())).toHaveLength(0);
  });

  it("draws the candidates the API returned, unchanged, when asked", () => {
    world.markerCalls.length = 0;

    render(
      <Chart
        bars={BARS}
        channel={null}
        signal={null}
        extrema={EXTREMA}
        mode="CURRENT REFIT"
        showCandidates
      />,
    );

    expect(lastMarks()).toHaveLength(3);
    expect(candidateMarks(lastMarks())).toHaveLength(2);
  });

  it("follows the switch without piling up series", () => {
    world.markerCalls.length = 0;
    world.series.length = 0;
    const props = { bars: BARS, channel: null, signal: null, extrema: EXTREMA, mode: "CURRENT REFIT" as const };

    const { rerender } = render(<Chart {...props} />);
    rerender(<Chart {...props} showCandidates />);
    expect(candidateMarks(lastMarks())).toHaveLength(2);

    rerender(<Chart {...props} showCandidates={false} />);
    expect(candidateMarks(lastMarks())).toHaveLength(0);
    expect(world.series.filter((s) => s.kind === "candles" && !s.removed)).toHaveLength(1);
  });

  it("still withholds a candidate nobody could have seen at the chosen instant, even when asked", () => {
    world.markerCalls.length = 0;

    render(
      <Chart
        bars={BARS}
        channel={null}
        signal={null}
        extrema={EXTREMA}
        mode="AS-SEEN-THEN"
        focusAtNs={BASE + 8n * STEP}
        showCandidates
      />,
    );

    // k1 was observed at step 7 (visible at step 8), k2 at step 9 (not yet).
    expect(candidateMarks(lastMarks())).toHaveLength(1);
  });

  it("draws nothing extra, and does not throw, when asked and the extrema request failed", () => {
    world.markerCalls.length = 0;

    expect(() =>
      render(
        <Chart
          bars={BARS}
          channel={null}
          signal={null}
          extrema={{ confirmed: [], candidates: [] }}
          mode="CURRENT REFIT"
          showCandidates
        />,
      ),
    ).not.toThrow();
    expect(lastMarks()).toHaveLength(0);
  });
});
