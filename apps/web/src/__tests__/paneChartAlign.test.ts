// @trace: REQ-WP-092
//
// The lower pane is a chart on the main chart's time axis, and that axis is an index over the union of the
// series' times: two charts line up only if they hold the same sequence. So a bar without a value is a
// whitespace entry, a value goes to the bar whose window contains its instant, and nothing is invented.

import { describe, expect, it } from "vitest";

import { alignToBars, lineRuns, volumeBars } from "../paneChart";
import { toSeconds } from "../series";
import type { BarOut } from "../types";

const STEP = 60_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;

function bar(i: number, extras: Partial<BarOut> = {}): BarOut {
  const open = BASE + BigInt(i) * STEP;
  return {
    open_time_ns: open,
    close_time_ns: open + STEP,
    open: "100",
    high: "101",
    low: "99",
    close: "100",
    volume_base: String(i + 1),
    is_final: true,
    ...extras,
  };
}
const closeOf = (i: number): number => toSeconds(BASE + BigInt(i + 1) * STEP) as number;
const point = (at: bigint, value: number) => ({ at_ns: at, value });

describe("alignToBars", () => {
  it("holds one entry per bar at the candle's time, whitespace where a bar has no value", () => {
    const bars = Array.from({ length: 12 }, (_, i) => bar(i, i === 11 ? { is_final: false } : {}));
    const points = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10].map((i) => point(BASE + BigInt(i + 1) * STEP, i * 10));

    const aligned = alignToBars(bars, points);

    expect(aligned).toHaveLength(12);
    expect(aligned.map((a) => a.time)).toEqual(bars.map((_, i) => closeOf(i)));
    expect(aligned.filter((a) => a.value === undefined)).toHaveLength(2);
    expect(aligned[5]?.value).toBeUndefined();
    expect(aligned[11]?.value).toBeUndefined();
  });

  it("puts a point inside a bar on that bar, and shows the later of two in one bar", () => {
    const bars = [bar(0), bar(1)];
    const aligned = alignToBars(bars, [
      point(BASE + 10_000_000_000n, 1),
      point(BASE + 40_000_000_000n, 2),
      point(BASE + STEP + 5_000_000_000n, 9),
    ]);

    expect(aligned.map((a) => a.value)).toEqual([2, 9]);
  });

  it("puts a value stamped exactly at a bar's close on that bar, not on the next", () => {
    const bars = [bar(0), bar(1)];

    const aligned = alignToBars(bars, [point(BASE + STEP, 5)]);

    expect(aligned.map((a) => a.value)).toEqual([5, undefined]);
  });

  it("does not create an entry for a point that no bar contains", () => {
    const bars = [bar(0), bar(1)];

    const aligned = alignToBars(bars, [point(BASE - 10n * STEP, 7), point(BASE + 50n * STEP, 8)]);

    expect(aligned).toHaveLength(2);
    expect(aligned.every((a) => a.value === undefined)).toBe(true);
  });

  it("is empty with no bars and one entry with one bar", () => {
    expect(alignToBars([], [point(BASE, 1)])).toEqual([]);
    expect(alignToBars([bar(0)], [point(BASE + STEP, 3)])).toEqual([{ time: closeOf(0), value: 3 }]);
  });

  it("does not depend on the order the bars or the points arrive in", () => {
    const bars = [bar(2), bar(0), bar(1)];
    const points = [point(BASE + 3n * STEP, 3), point(BASE + STEP, 1), point(BASE + 2n * STEP, 2)];

    expect(alignToBars(bars, points).map((a) => a.value)).toEqual([1, 2, 3]);
  });
});

describe("lineRuns", () => {
  it("is one value-only series per run and never joins two", () => {
    const bars = [bar(0), bar(1), bar(2), bar(3)];
    const parts = [
      [point(BASE + STEP, 1), point(BASE + 2n * STEP, 2)],
      [point(BASE + 3n * STEP, -5), point(BASE + 4n * STEP, -4)],
    ];

    const runs = lineRuns(bars, parts);

    expect(runs.map((run) => run.map((p) => p.value))).toEqual([[1, 2], [-5, -4]]);
    expect(runs[0]?.every((p) => p.value !== undefined)).toBe(true);
  });
});

describe("volumeBars", () => {
  it("colours each bar by its candle's direction and leaves a forming bar as whitespace", () => {
    const bars = [
      bar(0, { open: "100", close: "101" }),
      bar(1, { open: "101", close: "100" }),
      bar(2, { open: "100", close: "100" }),
      bar(3, { is_final: false }),
    ];

    const out = volumeBars(bars);

    expect(out.map((p) => p.time)).toEqual(bars.map((_, i) => closeOf(i)));
    expect(out.map((p) => p.color)).toEqual(["#26a69a", "#ef5350", "#26a69a", undefined]);
    expect(out[3]?.value).toBeUndefined();
    expect(out.map((p) => p.value)).toEqual([1, 2, 3, undefined]);
  });

  it("draws a bar of zero volume at zero and skips a value that is not a number", () => {
    const out = volumeBars([bar(0, { volume_base: "0" }), bar(1, { volume_base: "n/a" })]);

    expect(out[0]?.value).toBe(0);
    expect(out[1]?.value).toBeUndefined();
  });
});
