// @trace: REQ-WP-084
//
// Which of PRD section 27.3's panes have anything behind them, decided from the series the page already loads
// and by the one definition of "has data" `paneSeries` already holds, and where the selection goes when its
// pane has nothing.

import { describe, expect, it } from "vitest";

import { availablePanes, chooseSelection, PANES } from "../panes";
import type { FeaturePointOut } from "../types";

const BASE_NS = 1788838800000000000n;
const point = (i: number, values: Record<string, number>): FeaturePointOut => ({
  at_ns: BASE_NS + BigInt(i) * 1_000_000_000n,
  values,
});

describe("which panes have data", () => {
  it("is exactly the panes whose feature some point carries", () => {
    const available = availablePanes([point(0, { ofi_1m: 1 }), point(1, { ofi_1m: 2, cvd_unknown: 9 })]);

    expect([...available]).toEqual(["ofi_1m"]);
  });

  it("is nothing for an empty series", () => {
    expect(availablePanes([]).size).toBe(0);
  });

  it("counts a value of zero as data", () => {
    expect(availablePanes([point(0, { cvd_base: 0 })]).has("cvd_base")).toBe(true);
  });

  it("does not drop a pane for the gaps inside its series", () => {
    const available = availablePanes([point(0, { cvd_base: 1 }), point(1, {}), point(2, { cvd_base: 3 })]);

    expect(available.has("cvd_base")).toBe(true);
  });

  it("gives a name that is not one of the panes no pane", () => {
    const available = availablePanes([point(0, { some_other_feature: 1 })]);

    expect(available.size).toBe(0);
    expect(PANES.some((p) => p.feature === "some_other_feature")).toBe(false);
  });
});

describe("where the selection goes", () => {
  const some = new Set(["ofi_1m", "funding_z"]);

  it("keeps a choice that still has data", () => {
    expect(chooseSelection("funding_z", some)).toBe("funding_z");
  });

  it("moves to the first pane in the row that has data when the choice has none", () => {
    expect(chooseSelection("cvd", some)).toBe("ofi_1m");
  });

  it("selects nothing when no pane has data", () => {
    expect(chooseSelection("cvd", new Set())).toBeNull();
  });

  it("leaves the choice alone while it is not known which panes have data", () => {
    expect(chooseSelection("cvd", null)).toBe("cvd");
  });

  it("stays on nothing while nothing has data, and wakes up on the first pane that does", () => {
    expect(chooseSelection(null, new Set())).toBeNull();
    expect(chooseSelection(null, some)).toBe("ofi_1m");
  });
});
