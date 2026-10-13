// @trace: REQ-WP-106
//
// The bar of a timeframe above one minute that is still being built (REQ-WP-106): made from the minutes, stored and live, after the
// last stored bar of that timeframe. The stored table has only closed windows -- a 4h bar appears hours after it opened and the resampler
// runs every few minutes -- so without this the chart's last candle is the previous window and the current price is nowhere on it.

import { describe, expect, it } from "vitest";

import { aggregate, bucketOpen, formingBars, mergeMinutes } from "../live";
import type { BarOut } from "../types";

const MIN = 60_000_000_000n;
const HOUR = 60n * MIN;
const FOUR_H = 4n * HOUR;
// A 4h boundary, so windows are easy to read.
const T0 = 1_788_800_000_000_000_000n - (1_788_800_000_000_000_000n % FOUR_H);

const minute = (m: number, over: Partial<BarOut> = {}): BarOut => ({
  open_time_ns: T0 + BigInt(m) * MIN,
  close_time_ns: T0 + BigInt(m + 1) * MIN,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "1",
  is_final: true,
  ...over,
});
const stored4h = (index: number): BarOut => ({
  open_time_ns: T0 + BigInt(index) * FOUR_H,
  close_time_ns: T0 + BigInt(index + 1) * FOUR_H,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "240",
  is_final: true,
});
const run = (from: number, to: number, over: (m: number) => Partial<BarOut> = () => ({})): BarOut[] =>
  Array.from({ length: to - from + 1 }, (_, i) => minute(from + i, over(from + i)));

describe("bucketOpen", () => {
  it("is the opening instant of the window an instant falls in, from any known window's open", () => {
    expect(bucketOpen(T0 + 5n * HOUR, FOUR_H, T0)).toBe(T0 + FOUR_H);
    expect(bucketOpen(T0 + FOUR_H, FOUR_H, T0)).toBe(T0 + FOUR_H);
    expect(bucketOpen(T0 + FOUR_H - 1n, FOUR_H, T0)).toBe(T0);
  });

  it("follows the anchor's alignment, not the epoch's: a window that opens on a Monday stays on Mondays", () => {
    const week = 7n * 24n * HOUR;
    const monday = 1_789_344_000_000_000_000n; // 2026-09-14, a Monday 00:00 UTC

    expect(bucketOpen(monday + 3n * 24n * HOUR, week, monday)).toBe(monday);
    expect(bucketOpen(monday + week + 1n, week, monday)).toBe(monday + week);
  });
});

describe("mergeMinutes", () => {
  it("lets a stored minute supersede the live one for the same minute", () => {
    const got = mergeMinutes([minute(0, { close: "STORED" })], [minute(0, { close: "LIVE" }), minute(1)]);

    expect(got.map((b) => b.close)).toEqual(["STORED", "100"]);
  });

  it("is oldest first, and each minute once", () => {
    const got = mergeMinutes([minute(2), minute(0)], [minute(1), minute(2)]);

    expect(got.map((b) => b.open_time_ns)).toEqual([T0, T0 + MIN, T0 + 2n * MIN]);
  });
});

describe("aggregate", () => {
  it("is the first open, the highest high, the lowest low, the last close and the summed volume", () => {
    const bars = [
      minute(0, { open: "100", high: "103", low: "99", close: "102", volume_base: "2" }),
      minute(1, { open: "102", high: "110", low: "101", close: "108", volume_base: "3" }),
      minute(2, { open: "108", high: "109", low: "95", close: "96", volume_base: "5" }),
    ];

    expect(aggregate(bars, T0, FOUR_H)).toMatchObject({
      open_time_ns: T0,
      close_time_ns: T0 + FOUR_H,
      open: "100",
      high: "110",
      low: "95",
      close: "96",
      volume_base: "10",
    });
  });

  it("is not final: a window that is still open is not a bar", () => {
    expect(aggregate([minute(0)], T0, FOUR_H)!.is_final).toBe(false);
  });

  it("is nothing for no minutes", () => {
    expect(aggregate([], T0, FOUR_H)).toBeNull();
  });
});

describe("formingBars", () => {
  it("builds the window in progress after the last stored bar, with the current price as its close", () => {
    const stored = [stored4h(0)];
    const minutes = run(240, 300, (m) => ({ close: String(200 + (m - 240)) }));

    const got = formingBars({ stored, minutes, tfNs: FOUR_H });

    expect(got).toHaveLength(1);
    expect(got[0]).toMatchObject({ open_time_ns: T0 + FOUR_H, close_time_ns: T0 + 2n * FOUR_H, close: "260", is_final: false });
  });

  it("takes the high and low over every minute so far, not just the live ones", () => {
    const minutes = [...run(240, 250, () => ({ high: "150", low: "90" })), ...run(251, 255, () => ({ high: "120", low: "95" }))];

    const [bar] = formingBars({ stored: [stored4h(0)], minutes, tfNs: FOUR_H });

    expect(bar).toMatchObject({ high: "150", low: "90" });
  });

  it("also builds a window that closed but has not been stored yet, and says it is final only if every minute is there", () => {
    // 4h window 1 (minutes 240-479) is closed; the resampler has not made it yet. Window 2 is forming.
    const complete = run(240, 479);
    const forming = run(480, 490);

    const got = formingBars({ stored: [stored4h(0)], minutes: [...complete, ...forming], tfNs: FOUR_H });

    expect(got.map((b) => [b.open_time_ns, b.is_final])).toEqual([
      [T0 + FOUR_H, true],
      [T0 + 2n * FOUR_H, false],
    ]);
  });

  it("does not call a closed window final when a minute is missing from it", () => {
    const withHole = run(240, 479).filter((b) => b.open_time_ns !== T0 + 300n * MIN);

    const got = formingBars({ stored: [stored4h(0)], minutes: [...withHole, ...run(480, 481)], tfNs: FOUR_H });

    expect(got[0]!.is_final).toBe(false);
  });

  it("does not call a window final while any of its minutes is itself still forming", () => {
    const got = formingBars({
      stored: [stored4h(0)],
      minutes: [...run(240, 478), minute(479, { is_final: false })],
      tfNs: FOUR_H,
    });

    expect(got.at(-1)!.is_final).toBe(false);
  });

  it("is nothing when there are no minutes, so a feed that is down changes nothing", () => {
    expect(formingBars({ stored: [stored4h(0)], minutes: [], tfNs: FOUR_H })).toEqual([]);
  });

  it("starts at the first minute's window when nothing is stored", () => {
    const [bar] = formingBars({ stored: [], minutes: run(5, 20), tfNs: FOUR_H });

    expect(bar!.open_time_ns).toBe(T0);
  });

  it("builds nothing before the last stored bar's close: a stored window is not drawn twice", () => {
    const got = formingBars({ stored: [stored4h(0), stored4h(1)], minutes: run(0, 100), tfNs: FOUR_H });

    expect(got).toEqual([]);
  });

  it("never builds more than a handful of windows, whatever the gap", () => {
    const got = formingBars({ stored: [stored4h(0)], minutes: [minute(240), minute(240 * 40)], tfNs: FOUR_H });

    expect(got.length).toBeLessThanOrEqual(8);
  });
});
