// @trace: REQ-WP-061
//
// The conversion boundary. Every `_ns` the API sends is turned into a `bigint`
// here, once, and a value that is not a time has to become a stated load failure
// rather than an exception inside a render (REQ-WP-009's FR-016).

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchBars,
  fetchChannel,
  fetchDexDepth,
  fetchFeatureSeries,
  fetchTimeframes,
} from "../api";

const EXACT = "1789000000123456789";

function respondWith(payload: unknown, ok = true): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok, status: 200, json: async () => payload })),
  );
}

function lastUrl(): string {
  const mock = globalThis.fetch as unknown as { mock: { calls: [string][] } };
  return mock.mock.calls.at(-1)![0];
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("times coming in", () => {
  it("become bigints, exactly", async () => {
    respondWith({
      bars: [
        {
          open_time_ns: EXACT,
          close_time_ns: "1789000060123456789",
          open: "1",
          high: "2",
          low: "0",
          close: "1",
          volume_base: "10",
          is_final: true,
        },
      ],
    });

    const result = await fetchBars({ venue: "binance", symbol: "BTCUSDT", timeframeNs: 60e9 });

    expect(result.ok).toBe(true);
    const bar = result.ok ? result.value.bars[0]! : null;
    expect(bar?.open_time_ns).toBe(1789000000123456789n);
  });

  it("leaves a duration a number", async () => {
    respondWith({
      decision: { timeframe_ns: 60_000_000_000, opened_at_ns: EXACT },
    });

    const result = await fetchFeatureSeries({
      venue: "binance",
      symbol: "BTCUSDT",
      timeframeNs: 60e9,
      startNs: 0n,
      endNs: 1n,
    });

    expect(result.ok).toBe(true);
    const decision = result.ok
      ? (result.value as unknown as { decision: { timeframe_ns: unknown; opened_at_ns: unknown } })
          .decision
      : null;
    expect(typeof decision?.timeframe_ns).toBe("number");
    expect(typeof decision?.opened_at_ns).toBe("bigint");
  });

  it("keeps a null instant null, because null is an answer", async () => {
    respondWith({
      chain_id: 999,
      pool: "0xpool",
      requested_at_ns: EXACT,
      state_time_ns: null,
      bands: [],
    });

    const result = await fetchDexDepth({ chainId: 999, pool: "0xpool", atNs: 1789n });

    expect(result.ok && result.value.state_time_ns).toBeNull();
    expect(result.ok && result.value.requested_at_ns).toBe(1789000000123456789n);
  });

  it("converts inside arrays and nested objects", async () => {
    respondWith({ points: [{ at_ns: EXACT, values: { cvd: 1 } }] });

    const result = await fetchFeatureSeries({
      venue: "binance",
      symbol: "BTCUSDT",
      timeframeNs: 60e9,
      startNs: 0n,
      endNs: 1n,
    });

    expect(result.ok && result.value.points[0]!.at_ns).toBe(1789000000123456789n);
  });
});

describe("a time that is not one", () => {
  it.each([["", "empty"], ["12.5", "fractional"], ["abc", "not a number"], ["-1", "negative"]])(
    "is a stated failure rather than a crash in a render (%s: %s)",
    async (bad) => {
      respondWith({ points: [{ at_ns: bad, values: {} }] });

      const result = await fetchFeatureSeries({
        venue: "binance",
        symbol: "BTCUSDT",
        timeframeNs: 60e9,
        startNs: 0n,
        endNs: 1n,
      });

      expect(result.ok).toBe(false);
      expect(!result.ok && result.error).toMatch(/unreadable time/);
      expect(!result.ok && result.error).toContain("points[0].at_ns");
    },
  );

  it("names the field, so the server's mistake is findable", async () => {
    respondWith({
      bars: [{ open_time_ns: EXACT, close_time_ns: "oops" }],
    });

    const result = await fetchBars({ venue: "binance", symbol: "BTCUSDT", timeframeNs: 60e9 });

    expect(!result.ok && result.error).toContain("bars[0].close_time_ns");
  });
});

describe("times going out", () => {
  it("are sent exactly, not through a number", async () => {
    respondWith({ as_of_ns: EXACT, source_max_event_time_ns: EXACT });

    await fetchChannel({
      venue: "binance",
      symbol: "BTCUSDT",
      timeframeNs: 60e9,
      atNs: 1789000000123456789n,
      mode: "AS_SEEN_THEN" as never,
    });

    // Rounding this on the way out asks the server about a different moment
    // than the chart is showing -- which for `as_of_ns` is the look-ahead rule.
    expect(lastUrl()).toContain("at_ns=1789000000123456789");
    expect(lastUrl()).not.toContain("1789000000123456800");
  });
});

describe("the offered set", () => {
  it("is read from its own route", async () => {
    respondWith({ timeframes: [{ token: "1m", timeframe_ns: 60_000_000_000 }] });

    const result = await fetchTimeframes();

    expect(lastUrl()).toContain("/api/v1/timeframes");
    expect(result.ok && result.value.timeframes[0]?.token).toBe("1m");
  });

  it("leaves each duration a number, not a bigint", async () => {
    respondWith({ timeframes: [{ token: "15m", timeframe_ns: 900_000_000_000 }] });

    const result = await fetchTimeframes();

    const value = result.ok ? result.value.timeframes[0]?.timeframe_ns : null;
    expect(value).toBe(900_000_000_000);
    expect(typeof value).toBe("number");
  });
});
