// @trace: REQ-WP-089

import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchVolumeProfile } from "../api";

const BODY = {
  venue: "binance",
  symbol: "BTCUSDT",
  window: "24h",
  window_ns: 86_400_000_000_000,
  as_of_ns: "1789000000123456789",
  covers_from_ns: "1788990000000000000",
  covered_ns: 600_000_000_000,
  complete: false,
  bin_width: "20",
  left_out_rows: 0,
  bins: [{ low: "100", high: "120", buy: "1", sell: "2", unknown: "0", trades: 3 }],
  poc_index: 0,
  poc_tie: false,
  value_area_low: "100",
  value_area_high: "120",
  value_area_is_whole_profile: true,
};

function respondWith(payload: unknown, ok = true, status = 200): void {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok, status, json: async () => payload })));
}
const lastUrl = (): string => (globalThis.fetch as unknown as { mock: { calls: [string][] } }).mock.calls.at(-1)![0];

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchVolumeProfile", () => {
  it("asks for the series and the window, and for an instant only when it has one", async () => {
    respondWith(BODY);

    await fetchVolumeProfile({ venue: "binance", symbol: "BTCUSDT", window: "24h", atNs: null });
    expect(lastUrl()).toContain("/api/v1/volume-profile?");
    expect(lastUrl()).toContain("venue=binance");
    expect(lastUrl()).toContain("symbol=BTCUSDT");
    expect(lastUrl()).toContain("window=24h");
    expect(lastUrl()).not.toContain("at_ns");

    await fetchVolumeProfile({ venue: "binance", symbol: "BTCUSDT", window: "4h", atNs: 1789000000123456789n });
    expect(lastUrl()).toContain("at_ns=1789000000123456789");
  });

  it("turns the instants into bigints exactly and keeps the durations as numbers", async () => {
    respondWith(BODY);

    const result = await fetchVolumeProfile({ venue: "binance", symbol: "BTCUSDT", window: "24h", atNs: null });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.as_of_ns).toBe(1789000000123456789n);
      expect(result.value.covers_from_ns).toBe(1788990000000000000n);
      expect(result.value.window_ns).toBe(86_400_000_000_000);
      expect(result.value.covered_ns).toBe(600_000_000_000);
      expect(result.value.bins[0]?.buy).toBe("1");
    }
  });

  it("states a refusal by its status: 404 is 'nothing collected', not a crash", async () => {
    respondWith({ detail: "no price bins" }, false, 404);

    const result = await fetchVolumeProfile({ venue: "binance", symbol: "BTCUSDT", window: "24h", atNs: null });

    expect(result).toEqual({ ok: false, error: "HTTP 404" });
  });
});
