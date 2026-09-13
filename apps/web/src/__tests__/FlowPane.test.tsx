// @trace: REQ-WP-027
//
// The component decides nothing -- `panes.test.ts` covers that. What is worth
// asserting here is the part a reader sees and a decision module cannot: that
// the three empty-ish states produce three different messages, that a failure
// is never drawn as a pane, and that selecting replaces rather than adds.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FlowPane } from "../FlowPane";
import type { FeaturePointOut } from "../types";

const BASE_NS = 1788838800000000000n;

function points(values: Record<string, number>[]): FeaturePointOut[] {
  return values.map((v, i) => ({ at_ns: BASE_NS + BigInt(i) * 1_000_000_000n, values: v }));
}

describe("the pane a reader sees", () => {
  it("offers every pane and marks the selected one", () => {
    render(<FlowPane points={points([{ cvd: 1 }])} feature="cvd" onSelect={() => {}} />);

    expect(screen.getByRole("button", { name: "CVD" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "OFI (1m)" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("replaces rather than adds when another is chosen", () => {
    const onSelect = vi.fn();
    render(<FlowPane points={points([{ cvd: 1 }])} feature="cvd" onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: "OFI (1m)" }));

    expect(onSelect).toHaveBeenCalledWith("ofi_1m");
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("draws a line when there is something to draw", () => {
    render(
      <FlowPane points={points([{ cvd: 1 }, { cvd: 3 }])} feature="cvd" onSelect={() => {}} />,
    );

    expect(screen.getByRole("img", { name: /cvd over 2 point/ })).toBeInTheDocument();
  });

  it("says the window is empty rather than drawing nothing", () => {
    render(<FlowPane points={[]} feature="cvd" onSelect={() => {}} />);

    expect(screen.getByRole("status", { name: /Pane/ })).toHaveTextContent(/no feature points/i);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("says the feature is unavailable, in different words", () => {
    // A reader seeing this should look for the feature, not the window -- so
    // the two messages must not be the same sentence.
    render(<FlowPane points={points([{ ofi_1m: 1 }])} feature="cvd" onSelect={() => {}} />);

    expect(screen.getByRole("status", { name: /Pane/ })).toHaveTextContent(/no cvd readings/i);
  });

  it("never draws a failed load as a pane", () => {
    // REQ-WP-009's FR-016. A failure rendered as an empty pane is the
    // indistinguishable blank the rule forbids.
    render(
      <FlowPane points={[]} feature="cvd" onSelect={() => {}} failure="HTTP 503" />,
    );

    expect(screen.getByRole("status", { name: /Pane/ })).toHaveTextContent(/HTTP 503/);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("keeps a failure and an empty window apart", () => {
    const failed = render(
      <FlowPane points={[]} feature="cvd" onSelect={() => {}} failure="HTTP 503" />,
    );
    const failedText = screen.getByRole("status", { name: /Pane/ }).textContent;
    failed.unmount();

    render(<FlowPane points={[]} feature="cvd" onSelect={() => {}} />);

    expect(screen.getByRole("status", { name: /Pane/ }).textContent).not.toBe(failedText);
  });
});
