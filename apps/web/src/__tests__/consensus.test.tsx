// @trace: REQ-WP-091
//
// The consensus layer (spec US3, FR-004): an optional line over the candles at each bar's
// consensus mid, drawn only where at least two venues contributed, a gap where fewer did with
// the reason said out loud, and nothing at all when the layer is off or there is no consensus
// data. `Chart` takes no `consensus` prop yet and the overlay list knows no "consensus", which
// is what these tests are red about -- T016-T019 give them the layer.

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OVERLAYS } from "../types";
import type { BarOut, ChannelOut, Overlay } from "../types";

const world = vi.hoisted(() => ({
  lineSeries: [] as { options: Record<string, unknown>; data: unknown[] | null }[],
}));

vi.mock("lightweight-charts", () => {
  // Every line series the chart creates, with the options it was created with and the data it
  // was last handed -- so a test can ask which series exist and what each of them draws.
  const line = (options: Record<string, unknown>) => {
    const entry = { options, data: null as unknown[] | null };
    world.lineSeries.push(entry);
    return {
      setData: (data: unknown[]) => {
        entry.data = data;
      },
      setMarkers: () => undefined,
      createPriceLine: () => ({}),
    };
  };
  const candles = () => ({
    setData: () => undefined,
    setMarkers: () => undefined,
    createPriceLine: () => ({}),
    attachPrimitive: () => undefined,
    detachPrimitive: () => undefined,
  });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: candles,
      addLineSeries: line,
      removeSeries: () => undefined,
      timeScale: () => ({ fitContent: () => undefined, setVisibleLogicalRange: () => undefined }),
      remove: () => undefined,
    }),
  };
});

import { Chart } from "../Chart";
import { toSeconds } from "../series";

// The real `ConsensusOut` lives in `types.ts` (T018) and does not exist yet; this is the shape
// `/api/v1/consensus` returns per bar (spec "Key Entities"): the mid when there is one, how many
// venues stood behind it, and why not when there is none.
type ConsensusPoint = {
  bar_close_ns: bigint;
  consensus_mid: string | null;
  venue_count: number;
  refusal_reason: string | null;
};

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
const bars = (count: number) => Array.from({ length: count }, (_, i) => bar(i));

const point = (
  b: BarOut,
  consensus_mid: string | null,
  venue_count: number,
  refusal_reason: string | null = null,
): ConsensusPoint => ({
  bar_close_ns: b.close_time_ns,
  consensus_mid,
  venue_count,
  refusal_reason,
});

// The consensus mids sit far from the candles and the channel (both around 100), so a value of
// theirs can never be mistaken for a channel's own point.
const MID = "2500.5";

const channel = (): ChannelOut => ({
  as_of_ns: bar(3).close_time_ns,
  model_name: "cmmf",
  model_version: "v1",
  lookback: 100,
  center_now: 100,
  upper_now: 102,
  lower_now: 98,
  slope_normalized: 0,
  slope_log_per_bar: 0,
  width_pct: 4,
  quality_score: 1,
  source_max_event_time_ns: bar(3).close_time_ns,
  mode: "AS-SEEN-THEN",
});

// The layer's name. `Chart`'s `overlays` prop is typed as `Overlay`, and `overlays.ts` discards a
// deep link whole when it names a layer this list does not know -- so without the name in
// `OVERLAYS` the layer cannot be on or off anywhere, not by toggle and not by link (FR-004's
// "optional layer" needs the option to exist).
const CONSENSUS_LAYER: Overlay = "consensus";
const layerOn: readonly Overlay[] = ["candles", CONSENSUS_LAYER];
const layerOff: readonly Overlay[] = ["candles", "channel_center", "channel_bounds"];

beforeEach(() => {
  world.lineSeries.length = 0;
});

describe("the chart and the cross-venue consensus line", () => {
  it("adds one line series at the consensus mids, one point per bar, when the layer is on", () => {
    const chartBars = bars(3);
    const mids = ["2500.5", "2501.25", "2499.75"];
    const consensus = chartBars.map((b, i) => point(b, mids[i], 2));

    render(<Chart bars={chartBars} channel={null} signal={null} overlays={layerOn} consensus={consensus} />);

    // `channel={null}` means the only line series on the chart can be the consensus one.
    expect(world.lineSeries).toHaveLength(1);
    // One point per bar: the time is the bar's close in seconds, the value its consensus mid.
    expect(world.lineSeries[0]?.data).toEqual(
      chartBars.map((b, i) => ({ time: toSeconds(b.close_time_ns), value: Number(mids[i]) })),
    );
  });

  it("adds no consensus series when the layer is off -- the channel's own lines and nothing else", () => {
    // The layer has to be a name the overlay list knows before "off" is a choice: this absence
    // below is already true while the layer does not exist, and a layer nobody can name can
    // never be switched on for the line above to be drawn.
    expect(OVERLAYS).toContain(CONSENSUS_LAYER);

    const chartBars = bars(4);
    const consensus = chartBars.map((b) => point(b, MID, 2));

    render(<Chart bars={chartBars} channel={channel()} signal={null} overlays={layerOff} consensus={consensus} />);

    // centre, upper, lower -- three, with no fourth.
    expect(world.lineSeries).toHaveLength(3);
    const drawn = world.lineSeries.flatMap((series) => (series.data ?? []) as { value: number }[]);
    expect(drawn.map((p) => p.value)).not.toContain(Number(MID));
  });

  it("leaves a gap where fewer than two venues contributed, and says why", () => {
    const chartBars = bars(4);
    const refused = chartBars[1];
    const consensus = [
      point(chartBars[0], MID, 2),
      point(refused, null, 1, "only 1 venue"),
      point(chartBars[2], "2501.25", 3),
      point(chartBars[3], "2499.75", 2),
    ];

    render(<Chart bars={chartBars} channel={null} signal={null} overlays={layerOn} consensus={consensus} />);

    expect(world.lineSeries).toHaveLength(1);
    const points = (world.lineSeries[0]?.data ?? []) as { time: number }[];
    // Three of the four bars: the refused one is absent from the line, the others in order.
    expect(points.map((p) => p.time)).toEqual([
      toSeconds(chartBars[0].close_time_ns),
      toSeconds(chartBars[2].close_time_ns),
      toSeconds(chartBars[3].close_time_ns),
    ]);
    expect(points.map((p) => p.time)).not.toContain(toSeconds(refused.close_time_ns));

    // The gap is not silent: a status names the refusal reason recorded for that bar.
    expect(screen.getByRole("status")).toHaveTextContent("only 1 venue");
  });

  it("draws nothing extra and does not crash when the consensus prop is null or absent", () => {
    // As above: this test only asserts what is *not* drawn, so it also pins that the layer is a
    // name the overlay list knows -- without it there is nothing here to be null.
    expect(OVERLAYS).toContain(CONSENSUS_LAYER);

    const chartBars = bars(3);

    const withNull = render(
      <Chart bars={chartBars} channel={null} signal={null} overlays={layerOn} consensus={null} />,
    );
    expect(withNull.getByTestId("chart")).toBeInTheDocument();
    expect(world.lineSeries).toHaveLength(0);
    expect(screen.queryByRole("status")).toBeNull();

    world.lineSeries.length = 0;
    render(<Chart bars={chartBars} channel={null} signal={null} overlays={layerOn} />);
    expect(world.lineSeries).toHaveLength(0);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
