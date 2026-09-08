// @trace: REQ-WP-009
//
// What the chart puts on screen, asserted through what a reader can see.
//
// jsdom has no layout engine, so `lightweight-charts` cannot measure its
// container and draws nothing. Asserting on canvas pixels is neither possible
// here nor useful -- the library's own rendering is its responsibility. What
// belongs to us is the *series data*: which candles, which lines, which bands,
// and where the marker goes. `buildSeries` is that decision, extracted so it
// can be checked without a renderer.
import { describe, expect, it } from "vitest";

import { buildSeries, markerFor } from "../series";
import type { BarOut, ChannelOut, SignalOut } from "../types";

const MINUTE_NS = 60 * 1_000_000_000;
const BASE_NS = 1_788_838_800_000_000_000;

function bar(i: number, close: number): BarOut {
  const open = BASE_NS + i * MINUTE_NS;
  return {
    open_time_ns: open,
    close_time_ns: open + MINUTE_NS,
    open: String(close),
    high: String(close + 5),
    low: String(close - 5),
    close: String(close),
    volume_base: "1",
    is_final: true,
  };
}

const CHANNEL: ChannelOut = {
  as_of_ns: BASE_NS + 3 * MINUTE_NS,
  model_name: "rolling_ols_log_price",
  model_version: "1.0.0",
  lookback: 60,
  center_now: 112_000,
  upper_now: 113_000,
  lower_now: 111_000,
  slope_normalized: -0.0037,
  width_pct: 0.024,
  quality_score: 0.83,
  source_max_event_time_ns: BASE_NS + 3 * MINUTE_NS,
  mode: "AS-SEEN-THEN",
};

const SIGNAL: SignalOut = {
  signal_id: "6f3d1a2e-8b47-5c19-9f2a-1d4e7c05b3a8",
  venue: "binance",
  symbol: "BTCUSDT",
  timeframe_ns: MINUTE_NS,
  direction: "short",
  boundary: "upper",
  state: "confirmed",
  opened_at_ns: BASE_NS + 3 * MINUTE_NS,
};

const BARS = [bar(0, 112_100), bar(1, 112_200), bar(2, 112_300), bar(3, 112_400)];

describe("chart series", () => {
  it("produces one candle per bar, in seconds, ascending", () => {
    const { candles } = buildSeries({ bars: BARS, channel: null });

    expect(candles).toHaveLength(4);
    expect(candles[0]).toMatchObject({ open: 112_100, high: 112_105, low: 112_095 });
    // lightweight-charts takes seconds, not nanoseconds. Feeding it
    // nanoseconds silently places every candle in the year 58,000.
    expect(candles[0].time).toBe(Math.floor((BASE_NS + MINUTE_NS) / 1e9));
    const times = candles.map((c) => c.time as number);
    expect(times).toEqual([...times].sort((a, b) => a - b));
  });

  it("draws the channel centre and both boundaries", () => {
    const { channelLines } = buildSeries({ bars: BARS, channel: CHANNEL });

    expect(Object.keys(channelLines)).toEqual(["center", "upper", "lower"]);
    expect(channelLines.center[0].value).toBe(112_000);
    expect(channelLines.upper[0].value).toBe(113_000);
    expect(channelLines.lower[0].value).toBe(111_000);
    expect(channelLines.center).toHaveLength(BARS.length);
  });

  it("draws the three zones as bands between the boundaries", () => {
    const { zones } = buildSeries({ bars: BARS, channel: CHANNEL });

    // width is 2,000; the upper zone spans 0.88..1.00 of it above the lower
    // boundary, so 111,000 + 1,760 to 113,000.
    expect(zones.upper.from).toBeCloseTo(112_760, 6);
    expect(zones.upper.to).toBeCloseTo(113_000, 6);
    expect(zones.middle.from).toBeCloseTo(111_880, 6);
    expect(zones.middle.to).toBeCloseTo(112_120, 6);
    expect(zones.lower.from).toBeCloseTo(111_000, 6);
    expect(zones.lower.to).toBeCloseTo(111_240, 6);
  });

  it("draws no channel and no zones when there is none", () => {
    // An absent channel is not a flat one. Drawing a zero line would put a
    // boundary on the chart that no model ever produced.
    const { channelLines, zones } = buildSeries({ bars: BARS, channel: null });

    expect(channelLines).toEqual({});
    expect(zones).toEqual({});
  });

  it("places the marker at the signal's instant, on its boundary", () => {
    const marker = markerFor(SIGNAL, CHANNEL);

    expect(marker.time).toBe(Math.floor(SIGNAL.opened_at_ns / 1e9));
    expect(marker.position).toBe("aboveBar");
    expect(marker.text).toContain("SHORT");
    expect(marker.text).toContain("upper");
  });

  it("places a long marker below the bar", () => {
    // Guard on the guard: a marker function ignoring direction would pass the
    // test above.
    const marker = markerFor({ ...SIGNAL, direction: "long", boundary: "lower" }, CHANNEL);

    expect(marker.position).toBe("belowBar");
    expect(marker.text).toContain("LONG");
  });

  it("returns no candles for no bars, rather than inventing one", () => {
    const { candles } = buildSeries({ bars: [], channel: CHANNEL });

    expect(candles).toEqual([]);
  });
});
