// @trace: REQ-WP-086
//
// A missing bar is visibly missing. A gap is found from two consecutive bars' own windows, so it cannot disagree with
// the bars; a bar that exists, whatever its volume, is never a gap.

import { describe, expect, it } from "vitest";

import { describeGap, findGaps, gapMarkers, noticeLines } from "../gaps";
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
    volume_base: "1",
    is_final: true,
    ...extras,
  };
}
const series = (indices: number[]): BarOut[] => indices.map((i) => bar(i));

describe("findGaps", () => {
  it("finds one gap of three in bars 0,1,2,6,7", () => {
    const gaps = findGaps(series([0, 1, 2, 6, 7]));

    expect(gaps).toHaveLength(1);
    expect(gaps[0]?.missing).toBe(3);
    expect(gaps[0]?.afterCloseNs).toBe(BASE + 3n * STEP);
    expect(gaps[0]?.beforeOpenNs).toBe(BASE + 6n * STEP);
  });

  it("finds a hole of exactly one bar, and two holes in one series", () => {
    expect(findGaps(series([0, 1, 3])).map((g) => g.missing)).toEqual([1]);
    expect(findGaps(series([0, 2, 3, 7])).map((g) => g.missing)).toEqual([1, 3]);
  });

  it("finds none in contiguous bars, in none and in one", () => {
    expect(findGaps(series([0, 1, 2, 3]))).toEqual([]);
    expect(findGaps([])).toEqual([]);
    expect(findGaps(series([5]))).toEqual([]);
  });

  it("does not treat the ends of the range as holes", () => {
    expect(findGaps(series([40, 41, 42]))).toEqual([]);
  });

  it("sorts the bars first", () => {
    expect(findGaps(series([7, 0, 2, 1, 6])).map((g) => g.missing)).toEqual([3]);
  });

  it("does not count a corrected bar with the same open as a gap", () => {
    expect(findGaps([bar(0), bar(1), bar(1, { close: "101" }), bar(2)])).toEqual([]);
  });

  it("does not count a bar of zero volume as missing: absence and quiet must not look alike", () => {
    expect(findGaps([bar(0), bar(1, { volume_base: "0" }), bar(2)])).toEqual([]);
  });

  it("rounds the count of a misaligned series and keeps the exact span", () => {
    const odd = bar(3, { open_time_ns: BASE + 3n * STEP + 20_000_000_000n, close_time_ns: BASE + 4n * STEP + 20_000_000_000n });

    const gaps = findGaps([bar(0), bar(1), odd]);

    expect(gaps[0]?.missing).toBe(1);
    expect(gaps[0]?.beforeOpenNs - gaps[0]!.afterCloseNs).toBe(STEP + 20_000_000_000n);
  });
});

describe("gapMarkers", () => {
  it("puts one amber marker at the first bar after each hole, stating how many are missing", () => {
    const bars = series([0, 1, 2, 6, 7]);

    const marks = gapMarkers(findGaps(bars), bars);

    expect(marks).toHaveLength(1);
    expect(marks[0]?.time).toBe(toSeconds(bar(6).close_time_ns));
    expect(marks[0]?.text).toBe("3 missing");
    expect(marks[0]?.shape).toBe("square");
    expect(marks[0]?.color).toBe("#f59f00");
  });

  it("is empty with no gaps and gives each marker an id of its own", () => {
    const bars = series([0, 2, 3, 7]);

    expect(gapMarkers([], bars)).toEqual([]);
    const marks = gapMarkers(findGaps(bars), bars);
    expect(new Set(marks.map((m) => m.id)).size).toBe(2);
  });
});

describe("the words for a gap", () => {
  it("states the number and the span in UTC, as DD.MM HH:mm", () => {
    const hour = 3_600_000_000_000n;
    const start = BigInt(Date.UTC(2026, 8, 26, 6, 0, 0)) * 1_000_000n; // 26.09 06:00 UTC
    const gap = { afterCloseNs: start + hour, beforeOpenNs: start + 149n * hour, missing: 148 };

    expect(describeGap(gap)).toBe("148 bars missing, 26.09 07:00 to 02.10 11:00");
  });

  it("says 'bar' for one", () => {
    const gap = { afterCloseNs: BASE, beforeOpenNs: BASE + STEP, missing: 1 };

    expect(describeGap(gap)).toMatch(/^1 bar missing, /);
  });

  it("lists the most recent first, at most five, and counts the rest", () => {
    const gaps = Array.from({ length: 8 }, (_, i) => ({
      afterCloseNs: BASE + BigInt(i * 10) * STEP,
      beforeOpenNs: BASE + BigInt(i * 10 + 2) * STEP,
      missing: i + 1,
    }));

    const lines = noticeLines(gaps);

    expect(lines).toHaveLength(6);
    expect(lines[0]).toMatch(/^8 bars missing/);
    expect(lines[4]).toMatch(/^4 bars missing/);
    expect(lines[5]).toBe("and 3 more");
  });

  it("has no lines for no gaps and no 'more' line for five or fewer", () => {
    expect(noticeLines([])).toEqual([]);
    expect(noticeLines(findGaps(series([0, 2, 4])))).toHaveLength(2);
  });
});
