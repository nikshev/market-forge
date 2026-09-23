// @trace: REQ-WP-074
//
// The row of timeframe buttons. It holds no state and touches no address: the
// page owns the in-force token so the displayed and requested values are the
// same value, which is the property FR-013 asks for.

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TimeframeControl } from "../TimeframeControl";
import type { TimeframeOption } from "../timeframes";

const OFFERED: TimeframeOption[] = [
  { token: "1m", timeframeNs: 60_000_000_000 },
  { token: "5m", timeframeNs: 300_000_000_000 },
  { token: "15m", timeframeNs: 900_000_000_000 },
  { token: "1h", timeframeNs: 3_600_000_000_000 },
];

describe("the timeframe control", () => {
  it("renders one button per offered option, in the order given", () => {
    render(<TimeframeControl offered={OFFERED} selected="15m" onSelect={() => {}} />);

    const buttons = screen.getAllByRole("button");
    expect(buttons.map((button) => button.textContent)).toEqual(["1m", "5m", "15m", "1h"]);
  });

  it("marks the in-force timeframe", () => {
    render(<TimeframeControl offered={OFFERED} selected="1h" onSelect={() => {}} />);

    expect(screen.getByRole("button", { name: "1h" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "15m" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reports the chosen token and nothing else", async () => {
    const onSelect = vi.fn();
    render(<TimeframeControl offered={OFFERED} selected="15m" onSelect={onSelect} />);

    await userEvent.click(screen.getByRole("button", { name: "5m" }));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("5m");
  });

  it("marks no button when the selected token is not offered", () => {
    // The page refuses an unoffered token before rendering the chart; the
    // control must not invent a selection to make itself look whole.
    render(<TimeframeControl offered={OFFERED} selected="7m" onSelect={() => {}} />);

    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveAttribute("aria-pressed", "false");
    }
  });
});
