// @trace: REQ-WP-085
//
// PRD section 27.3's first lower pane, volume, is a property of the bar and not of the features table, so
// its series is read from the loaded bars. What it must not do: draw a forming bar as if it were finished,
// skip a bar in which nothing traded, round what the API sent, or turn a bad value into a zero.

import { describe, expect, it } from "vitest";

import { volumeSeries } from "../panes";
import type { BarOut } from "../types";

const STEP = 900_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;

function bar(i: number, volume: string, isFinal = true): BarOut {
  const open = BASE + BigInt(i) * STEP;
  return {
    open_time_ns: open,
    close_time_ns: open + STEP,
    open: "100",
    high: "101",
    low: "99",
    close: "100",
    volume_base: volume,
    is_final: isFinal,
  };
}

describe("the volume series", () => {
  it("is one value per final bar, equal to its volume, at the instant the bar starts", () => {
    const bars = [...Array.from({ length: 12 }, (_, i) => bar(i, String(i + 1))), bar(12, "99", false)];

    const series = volumeSeries(bars);

    expect(series.state).toBe("ok");
    expect(series.points).toHaveLength(12);
    expect(series.points.map((p) => p.value)).toEqual(Array.from({ length: 12 }, (_, i) => i + 1));
    expect(series.points[0]?.at_ns).toBe(BASE);
  });

  it("leaves a bar that is still forming out", () => {
    const series = volumeSeries([bar(0, "5"), bar(1, "7", false)]);

    expect(series.points.map((p) => p.value)).toEqual([5]);
  });

  it("draws a bar in which nothing traded at zero, not as a gap", () => {
    const series = volumeSeries([bar(0, "5"), bar(1, "0"), bar(2, "3")]);

    expect(series.points.map((p) => p.value)).toEqual([5, 0, 3]);
  });

  it("keeps the value the API sent, to the digit", () => {
    const series = volumeSeries([bar(0, "12345.678901234")]);

    expect(series.points[0]?.value).toBe(12345.678901234);
  });

  it("skips a value that is not a number instead of drawing it as zero", () => {
    const series = volumeSeries([bar(0, "5"), bar(1, "not-a-number"), bar(2, "")]);

    expect(series.points.map((p) => p.value)).toEqual([5]);
  });

  it("orders by time whatever order the bars came in", () => {
    const series = volumeSeries([bar(2, "3"), bar(0, "1"), bar(1, "2")]);

    expect(series.points.map((p) => p.value)).toEqual([1, 2, 3]);
  });

  it("is empty with no final bar, and says so", () => {
    expect(volumeSeries([]).state).toBe("empty");
    expect(volumeSeries([bar(0, "5", false)]).state).toBe("empty");
  });

  it("is valid for a single bar and for bars of equal volume", () => {
    expect(volumeSeries([bar(0, "4")]).points).toHaveLength(1);
    expect(volumeSeries([bar(0, "4"), bar(1, "4")]).points.map((p) => p.value)).toEqual([4, 4]);
  });
});
