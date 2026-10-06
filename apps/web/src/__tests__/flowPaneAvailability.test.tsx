// @trace: REQ-WP-084
//
// The pane row says what exists before a button is pressed. A pane with no data is a disabled button whose
// name still says which pane it is; a pane with data is exactly the button it was; and "not known yet"
// (loading, or a failed load) is never "no data".

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FlowPane } from "../FlowPane";
import type { FeaturePointOut } from "../types";

const BASE_NS = 1788838800000000000n;
const points = (values: Record<string, number>[]): FeaturePointOut[] =>
  values.map((v, i) => ({ at_ns: BASE_NS + BigInt(i) * 1_000_000_000n, values: v }));

const OFI_ONLY = new Set(["ofi_1m"]);

describe("the pane row with some panes empty", () => {
  it("keeps the exact button for a pane with data", () => {
    render(
      <FlowPane
        points={points([{ ofi_1m: 1 }])}
        feature="ofi_1m"
        available={OFI_ONLY}
        onSelect={() => {}}
      />,
    );

    const button = screen.getByRole("button", { name: "OFI (1m)" });
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(button).toBeEnabled();
  });

  it("shows every other pane as a disabled button that says it has no data and which pane it is", () => {
    render(
      <FlowPane
        points={points([{ ofi_1m: 1 }])}
        feature="ofi_1m"
        available={OFI_ONLY}
        onSelect={() => {}}
      />,
    );

    const cvd = screen.getByRole("button", { name: "CVD (base) no data" });
    expect(cvd).toBeDisabled();
    // REQ-WP-091: 10th pane venue_basis_bps
    expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(9);
  });

  it("cannot be pressed into a selection", () => {
    let chosen = "";
    render(
      <FlowPane
        points={points([{ ofi_1m: 1 }])}
        feature="ofi_1m"
        available={OFI_ONLY}
        onSelect={(next) => {
          chosen = next;
        }}
      />,
    );

    screen.getByRole("button", { name: "CVD (base) no data" }).click();

    expect(chosen).toBe("");
  });

  it("says no pane has data, in a status, when none does and nothing is selected", () => {
    render(
      <FlowPane points={[]} feature={null} available={new Set()} onSelect={() => {}} />,
    );

    expect(screen.getByRole("status", { name: "Pane contents" })).toHaveTextContent(
      "No pane has data for this view",
    );
    // REQ-WP-091: 10th pane venue_basis_bps
    expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(10);
  });
});

describe("when it is not known which panes have data", () => {
  it("leaves every pane pressable and says 'no data' of none, while availability is null", () => {
    render(<FlowPane points={[]} feature="cvd" available={null} onSelect={() => {}} />);

    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
    expect(screen.getByRole("button", { name: "CVD (base)" })).toBeEnabled();
  });

  it("does the same when `available` is not given at all: the old behaviour exactly", () => {
    render(<FlowPane points={points([{ cvd: 1 }])} feature="cvd" onSelect={() => {}} />);

    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
  });

  it("shows a failure as a failure and no pane as 'no data'", () => {
    render(
      <FlowPane
        points={[]}
        feature="cvd"
        available={null}
        failure="HTTP 503"
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("status", { name: "Pane load" })).toHaveTextContent("HTTP 503");
    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
  });
});
