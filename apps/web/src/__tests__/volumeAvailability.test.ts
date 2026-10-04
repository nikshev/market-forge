// @trace: REQ-WP-085
//
// Volume is listed first in the pane row, ahead of the registered features, and is available whenever a final
// bar is: it does not wait for the feature series. `PANES` stays a list of registered features.

import { describe, expect, it } from "vitest";

import { availablePanes, BAR_PANES, chooseSelection, PANES, ROW } from "../panes";
import type { BarOut, FeaturePointOut } from "../types";

const BASE = 1_788_838_800_000_000_000n;
const STEP = 900_000_000_000n;

const bar = (i: number, isFinal = true): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "1",
  high: "1",
  low: "1",
  close: "1",
  volume_base: "1",
  is_final: isFinal,
});
const point = (values: Record<string, number>): FeaturePointOut => ({ at_ns: BASE, values });

describe("the pane row", () => {
  it("is volume first and then the registered features, which are unchanged", () => {
    expect(BAR_PANES.map((p) => p.feature)).toEqual(["volume"]);
    expect(ROW.map((p) => p.feature)).toEqual(["volume", ...PANES.map((p) => p.feature)]);
    expect(PANES.some((p) => p.feature === "volume")).toBe(false);
    expect(ROW[0]?.label).toBe("Volume");
  });
});

describe("which panes have data, with bars", () => {
  it("includes volume when a final bar exists, whatever the features say", () => {
    expect(availablePanes([], [bar(0)]).has("volume")).toBe(true);
    expect([...availablePanes([point({ ofi_1m: 1 })], [bar(0)])].sort()).toEqual(["ofi_1m", "volume"]);
  });

  it("leaves volume out when no bar is final, or there are none", () => {
    expect(availablePanes([point({ cvd: 1 })], [bar(0, false)]).has("volume")).toBe(false);
    expect(availablePanes([point({ cvd: 1 })], []).has("volume")).toBe(false);
  });

  it("is what it was for the features when no bars are given", () => {
    expect([...availablePanes([point({ cvd: 1 })])]).toEqual(["cvd"]);
  });
});

describe("where the selection goes, with volume in the row", () => {
  it("is volume when it is the first with data", () => {
    expect(chooseSelection("cvd", new Set(["volume", "ofi_1m"]))).toBe("volume");
  });

  it("keeps a reader's valid choice over volume", () => {
    expect(chooseSelection("ofi_1m", new Set(["volume", "ofi_1m"]))).toBe("ofi_1m");
  });

  it("is a feature pane when volume has none", () => {
    expect(chooseSelection("volume", new Set(["ofi_1m"]))).toBe("ofi_1m");
  });
});
