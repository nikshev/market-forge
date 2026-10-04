// @trace: REQ-WP-083
//
// PRD §27.5 calls the difference between the two channel views critical: a reader who cannot tell which one
// they have will read a refit as evidence the model saw what was coming. The mode is a chip, and the two chips
// must not look alike.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChannelModeControl } from "../ChannelMode";
import { AS_SEEN_THEN, CURRENT_REFIT } from "../types";

describe("the channel mode control", () => {
  it("names the mode in a chip and keeps the explanation and the switch", () => {
    render(<ChannelModeControl mode={AS_SEEN_THEN} onChange={() => undefined} />);

    expect(screen.getByRole("region", { name: "Channel mode" })).toBeInTheDocument();
    expect(screen.getByText(AS_SEEN_THEN).closest(".MuiChip-root")).not.toBeNull();
    expect(screen.getByText(/stored at this moment/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /show current refit/i })).toBeInTheDocument();
  });

  it("the two modes have chips of different colours", () => {
    const seen = render(<ChannelModeControl mode={AS_SEEN_THEN} onChange={() => undefined} />);
    const seenClass = seen.container.querySelector(".MuiChip-root")?.className;
    seen.unmount();

    const refit = render(<ChannelModeControl mode={CURRENT_REFIT} onChange={() => undefined} />);
    const refitClass = refit.container.querySelector(".MuiChip-root")?.className;

    expect(seenClass).toContain("MuiChip-colorPrimary");
    expect(refitClass).toContain("MuiChip-colorWarning");
    expect(seenClass).not.toEqual(refitClass);
  });

  it("the refit says in words what it is", () => {
    render(<ChannelModeControl mode={CURRENT_REFIT} onChange={() => undefined} />);

    expect(screen.getByText(/it has seen what followed/)).toBeInTheDocument();
  });
});
