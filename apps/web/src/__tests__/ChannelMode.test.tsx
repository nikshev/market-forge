// @trace: REQ-WP-009
//
// PRD section 27.5 makes the historical-versus-current distinction critical
// because it "directly exposes repaint-like differences". ADR-020 adds that
// the chart must always say which mode it is in: a reader who cannot tell will
// read a refit as evidence, and an unlabelled chart is worse than either mode.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChannelModeControl } from "../ChannelMode";
import { modeFromQuery } from "../deepLink";

describe("the channel mode control", () => {
  it("says which mode is showing", () => {
    render(<ChannelModeControl mode="AS-SEEN-THEN" onChange={() => {}} />);

    expect(screen.getByText(/AS-SEEN-THEN/)).toBeVisible();
  });

  it("says so for the refit too, in the same place", () => {
    render(<ChannelModeControl mode="CURRENT REFIT" onChange={() => {}} />);

    expect(screen.getByText(/CURRENT REFIT/)).toBeVisible();
  });

  it("explains what the refit means, where a reader will see it", () => {
    // The label alone is jargon. Someone who has not read PRD section 27.5
    // cannot know that one of these views has hindsight in it.
    render(<ChannelModeControl mode="CURRENT REFIT" onChange={() => {}} />);

    expect(screen.getByText(/refitted now/i)).toBeVisible();
  });

  it("switches modes when asked", async () => {
    const onChange = vi.fn();
    render(<ChannelModeControl mode="AS-SEEN-THEN" onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /current refit/i }));

    expect(onChange).toHaveBeenCalledWith("CURRENT REFIT");
  });
});

describe("the deep link's mode", () => {
  it("opens AS-SEEN-THEN by default", () => {
    // PRD section 27.5: "Default when opening signal deep-link: AS-SEEN-THEN."
    // Every alert this system has sent carries such a link.
    expect(modeFromQuery(new URLSearchParams(""))).toBe("AS-SEEN-THEN");
  });

  it("opens AS-SEEN-THEN when the parameter is unparseable", () => {
    // ADR-020: the default holds when the value cannot be read. A link mangled
    // by a mail client must not silently become a refit.
    expect(modeFromQuery(new URLSearchParams("as_seen_then=perhaps"))).toBe("AS-SEEN-THEN");
    expect(modeFromQuery(new URLSearchParams("as_seen_then="))).toBe("AS-SEEN-THEN");
  });

  it("honours an explicit refit request", () => {
    expect(modeFromQuery(new URLSearchParams("as_seen_then=false"))).toBe("CURRENT REFIT");
  });
});
