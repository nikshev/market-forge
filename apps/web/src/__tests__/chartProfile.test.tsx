// @trace: REQ-WP-089
//
// The chart attaches the profile as a series primitive on its candle series when the layer is on, replaces it when the
// profile changes, and takes it away with the series. With the layer off, or no profile, nothing is attached.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BarOut, VolumeProfileOut } from "../types";

const world = vi.hoisted(() => ({
  attached: [] as unknown[],
  detached: [] as unknown[],
}));

vi.mock("lightweight-charts", () => {
  const make = (kind: string) => ({
    kind,
    setData: () => undefined,
    setMarkers: () => undefined,
    createPriceLine: () => ({}),
    attachPrimitive: (p: unknown) => world.attached.push(p),
    detachPrimitive: (p: unknown) => world.detached.push(p),
  });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: () => make("candles"),
      addLineSeries: () => make("line"),
      removeSeries: () => undefined,
      timeScale: () => ({ fitContent: () => undefined, setVisibleLogicalRange: () => undefined }),
      remove: () => undefined,
    }),
  };
});

import { Chart } from "../Chart";

const bar = (i: number): BarOut => ({
  open_time_ns: 1_788_838_800_000_000_000n + BigInt(i) * 900_000_000_000n,
  close_time_ns: 1_788_838_800_000_000_000n + BigInt(i + 1) * 900_000_000_000n,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "1",
  is_final: true,
});
const BARS = [0, 1, 2].map(bar);
const profile = (window = "24h"): VolumeProfileOut => ({
  venue: "binance",
  symbol: "BTCUSDT",
  window,
  window_ns: 1,
  as_of_ns: 1n,
  covers_from_ns: 0n,
  covered_ns: 1,
  complete: false,
  bin_width: "10",
  left_out_rows: 0,
  bins: [{ low: "100", high: "110", buy: "1", sell: "1", unknown: "0", trades: 1 }],
  poc_index: 0,
  poc_tie: false,
  value_area_low: "100",
  value_area_high: "110",
  value_area_is_whole_profile: true,
});

describe("the chart and the volume profile layer", () => {
  it("attaches a primitive with the layer on and a profile", () => {
    world.attached.length = 0;

    render(<Chart bars={BARS} channel={null} signal={null} volumeProfile={profile()} />);

    expect(world.attached).toHaveLength(1);
  });

  it("attaches nothing with the layer off, or with no profile", () => {
    world.attached.length = 0;

    render(<Chart bars={BARS} channel={null} signal={null} overlays={["candles"]} volumeProfile={profile()} />);
    render(<Chart bars={BARS} channel={null} signal={null} volumeProfile={null} />);

    expect(world.attached).toHaveLength(0);
  });

  it("replaces the primitive when the profile changes, and detaches the old one", () => {
    world.attached.length = 0;
    world.detached.length = 0;
    const { rerender } = render(<Chart bars={BARS} channel={null} signal={null} volumeProfile={profile("24h")} />);

    rerender(<Chart bars={BARS} channel={null} signal={null} volumeProfile={profile("4h")} />);

    expect(world.attached).toHaveLength(2);
    expect(world.detached).toContain(world.attached[0]);
  });

  it("takes the primitive away when the profile goes", () => {
    world.attached.length = 0;
    world.detached.length = 0;
    const { rerender } = render(<Chart bars={BARS} channel={null} signal={null} volumeProfile={profile()} />);

    rerender(<Chart bars={BARS} channel={null} signal={null} volumeProfile={null} />);

    expect(world.detached).toContain(world.attached[0]);
  });
});
