// @trace: REQ-WP-088
//
// The CVD pane draws `cvd_base` and breaks its line where `cvd_run` changes: a running sum is not comparable
// across a missing bar or a missed trade, and a line joined across the break would say it is.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FlowPane } from "../FlowPane";
import { PANES, paneSeries, segments } from "../panes";
import type { FeaturePointOut } from "../types";

const BASE_NS = 1788838800000000000n;
const point = (i: number, values: Record<string, number>): FeaturePointOut => ({
  at_ns: BASE_NS + BigInt(i) * 60_000_000_000n,
  values,
});

describe("the CVD (base) pane", () => {
  it("is the cvd_base feature, labelled for its unit", () => {
    const pane = PANES.find((p) => p.feature === "cvd_base");

    expect(pane?.label).toBe("CVD (base)");
    expect(PANES.some((p) => p.feature === "cvd")).toBe(false);
  });

  it("is a live button with rows and reads 'no data' without", () => {
    const points = [point(0, { cvd_base: 1, cvd_run: 0 }), point(1, { cvd_base: 3, cvd_run: 0 })];
    const { rerender } = render(
      <FlowPane points={points} feature="cvd_base" available={new Set(["cvd_base"])} onSelect={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "CVD (base)" })).toBeEnabled();

    rerender(<FlowPane points={[]} feature={null} available={new Set()} onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: "CVD (base) no data" })).toBeDisabled();
  });
});

describe("where the line breaks", () => {
  it("splits the series where cvd_run changes, and not elsewhere", () => {
    const points = [
      point(0, { cvd_base: 1, cvd_run: 0 }),
      point(1, { cvd_base: 3, cvd_run: 0 }),
      point(2, { cvd_base: -2, cvd_run: 1 }),
      point(3, { cvd_base: 0, cvd_run: 1 }),
    ];

    const parts = segments(paneSeries(points, "cvd_base").points, points);

    expect(parts.map((part) => part.map((p) => p.value))).toEqual([[1, 3], [-2, 0]]);
  });

  it("keeps one segment for a series with no break and for a feature without runs", () => {
    const flat = [point(0, { cvd_base: 1, cvd_run: 0 }), point(1, { cvd_base: 2, cvd_run: 0 })];
    const noRun = [point(0, { ofi_1m: 1 }), point(1, { ofi_1m: 2 })];

    expect(segments(paneSeries(flat, "cvd_base").points, flat)).toHaveLength(1);
    expect(segments(paneSeries(noRun, "ofi_1m").points, noRun)).toHaveLength(1);
  });

  it("splits a feature series only on its own run, not on a gap in values", () => {
    const points = [
      point(0, { cvd_base: 1, cvd_run: 0 }),
      point(1, { cvd_run: 0 }),
      point(2, { cvd_base: 4, cvd_run: 0 }),
    ];

    expect(segments(paneSeries(points, "cvd_base").points, points)).toHaveLength(1);
  });
});
