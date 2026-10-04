// @trace: REQ-WP-082
//
// The channel as the model fitted it: a log-linear band over its lookback window, ending at the bar the
// snapshot was taken at. `level(i) = level_now * exp(slope * (i - last))`.
//
// The page used to repeat the *current* levels for every bar of the history, so a channel fitted to the last
// fifteen hours was drawn as a flat stripe across nine days. These tests pin the real shape.

import { describe, expect, it } from "vitest";

import { CHANNEL_STYLE, buildSeries, visibleRangeForChannel } from "../series";
import type { BarOut, ChannelOut } from "../types";

const STEP = 900_000_000_000n; // 15 minutes
const BASE = 1_788_838_800_000_000_000n;

function bar(i: number, close = 100): BarOut {
  const open = BASE + BigInt(i) * STEP;
  return {
    open_time_ns: open,
    close_time_ns: open + STEP,
    open: String(close),
    high: String(close + 1),
    low: String(close - 1),
    close: String(close),
    volume_base: "1",
    is_final: true,
  };
}

const closeOf = (i: number): bigint => BASE + BigInt(i + 1) * STEP;

function channel(overrides: Partial<ChannelOut> = {}): ChannelOut {
  return {
    as_of_ns: closeOf(11),
    model_name: "rolling_ols_log_price",
    model_version: "1.0.0",
    lookback: 5,
    center_now: 100,
    upper_now: 102,
    lower_now: 99,
    slope_normalized: 0.5,
    slope_log_per_bar: 0.01,
    width_pct: 3,
    quality_score: 0.8,
    source_max_event_time_ns: closeOf(11),
    mode: "AS-SEEN-THEN",
    ...overrides,
  };
}

const BARS = Array.from({ length: 12 }, (_, i) => bar(i));

describe("the channel is drawn over its window only", () => {
  it("each line has exactly `lookback` points, on the last bars of the window", () => {
    const { channelLines, candles } = buildSeries({ bars: BARS, channel: channel() });

    for (const name of ["center", "upper", "lower"]) {
      expect(channelLines[name]).toHaveLength(5);
      expect(channelLines[name].map((p) => p.time)).toEqual(candles.slice(-5).map((c) => c.time));
    }
  });

  it("is not stretched across the history: 12 bars on the chart, 5 in the channel", () => {
    const { channelLines, candles } = buildSeries({ bars: BARS, channel: channel() });

    expect(candles).toHaveLength(12);
    expect(channelLines.center).toHaveLength(5);
  });

  it("the last point is the `_now` value and each earlier one is that times exp(slope * -k)", () => {
    const { channelLines } = buildSeries({ bars: BARS, channel: channel() });

    const centre = channelLines.center.map((p) => p.value);
    expect(centre.at(-1)).toBeCloseTo(100, 9);
    expect(centre[0]).toBeCloseTo(100 * Math.exp(-0.04), 9);
    for (let i = 0; i < 5; i += 1) {
      expect(centre[i]).toBeCloseTo(100 * Math.exp(0.01 * (i - 4)), 9);
    }
    expect(channelLines.upper.at(-1)?.value).toBeCloseTo(102, 9);
    expect(channelLines.lower.at(-1)?.value).toBeCloseTo(99, 9);
  });

  it("rises when the slope is positive and falls when it is negative", () => {
    const up = buildSeries({ bars: BARS, channel: channel({ slope_log_per_bar: 0.01 }) });
    const down = buildSeries({ bars: BARS, channel: channel({ slope_log_per_bar: -0.01 }) });

    expect(up.channelLines.center[0].value).toBeLessThan(up.channelLines.center[4].value);
    expect(down.channelLines.center[0].value).toBeGreaterThan(down.channelLines.center[4].value);
  });

  it("keeps the bounds' ratio to the centre across the window", () => {
    const { channelLines } = buildSeries({ bars: BARS, channel: channel() });

    for (let i = 0; i < 5; i += 1) {
      expect(channelLines.upper[i].value / channelLines.center[i].value).toBeCloseTo(1.02, 9);
      expect(channelLines.lower[i].value / channelLines.center[i].value).toBeCloseTo(0.99, 9);
    }
  });

  it("a slope of exactly zero is a flat band over the window, as the model said", () => {
    const { channelLines } = buildSeries({ bars: BARS, channel: channel({ slope_log_per_bar: 0 }) });

    expect(new Set(channelLines.center.map((p) => p.value))).toEqual(new Set([100]));
    expect(channelLines.center).toHaveLength(5);
  });
});

describe("as seen then: the window ends where the snapshot was taken", () => {
  it("a channel stored at an earlier bar ends there although later bars exist", () => {
    const { channelLines, candles } = buildSeries({
      bars: BARS,
      channel: channel({ as_of_ns: closeOf(7) }),
    });

    expect(channelLines.center).toHaveLength(5);
    expect(channelLines.center.at(-1)?.time).toBe(candles[7].time);
    expect(channelLines.center[0].time).toBe(candles[3].time);
  });

  it("uses no bar that closes after the snapshot", () => {
    const { channelLines, candles } = buildSeries({
      bars: BARS,
      channel: channel({ as_of_ns: closeOf(7) }),
    });
    const last = channelLines.center.at(-1)?.time as number;

    expect(last).toBeLessThanOrEqual(candles[7].time as number);
  });
});

describe("what is not drawn", () => {
  it("fewer bars than the lookback: the lines cover the bars there are", () => {
    const { channelLines } = buildSeries({
      bars: BARS.slice(0, 3),
      channel: channel({ lookback: 60, as_of_ns: closeOf(2) }),
    });

    expect(channelLines.center).toHaveLength(3);
  });

  it("a snapshot before the first bar draws no lines", () => {
    const { channelLines } = buildSeries({
      bars: BARS,
      channel: channel({ as_of_ns: BASE }),
    });

    expect(channelLines).toEqual({});
  });

  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    "a slope of %s draws no lines: an absent channel is not a flat one",
    (slope) => {
      const { channelLines } = buildSeries({
        bars: BARS,
        channel: channel({ slope_log_per_bar: slope }),
      });

      expect(channelLines).toEqual({});
    },
  );

  it("a response with no slope at all (an older server) draws no lines", () => {
    const old = channel() as unknown as Record<string, unknown>;
    delete old.slope_log_per_bar;

    const { channelLines } = buildSeries({ bars: BARS, channel: old as unknown as ChannelOut });

    expect(channelLines).toEqual({});
  });

  it("no channel, no lines (unchanged)", () => {
    expect(buildSeries({ bars: BARS, channel: null }).channelLines).toEqual({});
  });
});

describe("the view opens on the channel", () => {
  it("is the last two lookbacks of bars plus a margin, when there is more history", () => {
    const history = Array.from({ length: 800 }, (_, i) => bar(i));

    const range = visibleRangeForChannel(history, 60);

    expect(range).toEqual({ from: 800 - 1 - 120, to: 800 - 1 + 5 });
  });

  it("starts at the first bar when the history is shorter than that", () => {
    expect(visibleRangeForChannel(Array.from({ length: 50 }, (_, i) => bar(i)), 60)).toEqual({
      from: 0,
      to: 49 + 5,
    });
  });

  it("is nothing for no bars, so the chart fits its content as before", () => {
    expect(visibleRangeForChannel([], 60)).toBeNull();
  });
});

describe("the lines can be seen", () => {
  it("the centre is solid and at least twice as thick as it was (2)", () => {
    expect(CHANNEL_STYLE.center.lineStyle).toBe(0);
    expect(CHANNEL_STYLE.center.lineWidth).toBeGreaterThanOrEqual(4);
  });

  it("the bounds are at least twice as thick as they were (1) and use the zones' colours", () => {
    expect(CHANNEL_STYLE.upper.lineWidth).toBeGreaterThanOrEqual(2);
    expect(CHANNEL_STYLE.lower.lineWidth).toBeGreaterThanOrEqual(2);
    expect(CHANNEL_STYLE.upper.color).toBe("#d64545");
    expect(CHANNEL_STYLE.lower.color).toBe("#2f9e44");
  });
});
