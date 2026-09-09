// @trace: REQ-US-004

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExplanationPanel } from "../Explanation";
import { GROUPS } from "../types";
import type { ExplanationOut } from "../types";

const EXPLANATION: ExplanationOut = {
  top_positive: [
    { group: "channel_structure", value: 26, cap: 30, share: 26 / 30, names: ["slope"] },
  ],
  top_negative: [
    { group: "volume_confirmation", value: 1, cap: 10, share: 0.1, names: ["poc_far"] },
  ],
  missing: ["defi_crossvenue_context"],
  feature_snapshot: { ofi_1m: 0.62 },
  model_version: "deterministic-v1",
  factors: [
    { group: "channel_structure", value: 26, cap: 30, share: 26 / 30, names: ["slope"] },
    { group: "rejection_quality", value: 17, cap: 20, share: 0.85, names: ["wick"] },
    { group: "order_flow_confirmation", value: 16, cap: 20, share: 0.8, names: ["ofi"] },
    { group: "volume_confirmation", value: 1, cap: 10, share: 0.1, names: ["poc_far"] },
    { group: "derivatives_context", value: 8, cap: 10, share: 0.8, names: ["funding_z"] },
  ],
};

describe("ExplanationPanel", () => {
  it("shows every one of PRD section 22.1's six groups", () => {
    // SC-008. A group left off the panel because it had no data reads as "not
    // relevant", which is the opposite of what happened.
    render(<ExplanationPanel explanation={EXPLANATION} />);

    const rows = screen.getByRole("list", { name: "Contribution factors" });
    expect(rows.children).toHaveLength(GROUPS.length);
  });

  it("says a missing family is missing rather than showing a zero", () => {
    // SC-007. Zero is a measurement. "No data" is not one.
    render(<ExplanationPanel explanation={EXPLANATION} />);

    expect(screen.getByText(/no data — not scored, not zero/)).toBeInTheDocument();
  });

  it("distinguishes a family that scored zero from one that is absent", () => {
    // The volume group scored 1 of 10 -- weak, and present. It must not be
    // rendered the way the absent DeFi group is.
    render(<ExplanationPanel explanation={EXPLANATION} />);

    expect(screen.getByText("1 / 10")).toBeInTheDocument();
  });

  it("says so when a signal was never scored", () => {
    // FR-009. An empty list of factors would say it scored on nothing.
    render(<ExplanationPanel explanation={null} />);

    expect(screen.getByText(/was not scored/)).toBeInTheDocument();
  });
});
