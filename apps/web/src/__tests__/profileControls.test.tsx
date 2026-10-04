// @trace: REQ-WP-089

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProfileControls } from "../ProfileControls";
import type { VolumeProfileOut } from "../types";

const profile = (extras: Partial<VolumeProfileOut> = {}): VolumeProfileOut => ({
  venue: "binance",
  symbol: "BTCUSDT",
  window: "24h",
  window_ns: 86_400_000_000_000,
  as_of_ns: 1n,
  covers_from_ns: 0n,
  covered_ns: 200 * 60_000_000_000,
  complete: false,
  bin_width: "20",
  left_out_rows: 0,
  bins: [],
  poc_index: 0,
  poc_tie: false,
  value_area_low: "0",
  value_area_high: "0",
  value_area_is_whole_profile: false,
  ...extras,
});

describe("the profile's controls", () => {
  it("offers 4h, 24h and 7d with the chosen one pressed, 24h by default", () => {
    render(<ProfileControls window="24h" onWindow={() => {}} profile={null} state="loading" />);

    const group = screen.getByRole("group", { name: "Profile window" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "24h profile" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "4h profile" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "7d profile" })).toHaveAttribute("aria-pressed", "false");
  });

  it("asks for the window that is pressed", () => {
    const onWindow = vi.fn();
    render(<ProfileControls window="24h" onWindow={onWindow} profile={null} state="loading" />);

    fireEvent.click(screen.getByRole("button", { name: "4h profile" }));

    expect(onWindow).toHaveBeenCalledWith("4h");
  });

  it("says how much of its window the data covers", () => {
    render(<ProfileControls window="24h" onWindow={() => {}} profile={profile()} state="ok" />);

    expect(screen.getByRole("status", { name: "Volume profile" })).toHaveTextContent("covers 3 h 20 m of 24 h");
  });

  it("says nothing has been collected for a market rather than showing an empty profile", () => {
    render(<ProfileControls window="24h" onWindow={() => {}} profile={null} state="none" />);

    expect(screen.getByRole("status", { name: "Volume profile" })).toHaveTextContent(
      "no price bins collected for this market yet",
    );
  });

  it("states a failure as a failure", () => {
    render(<ProfileControls window="24h" onWindow={() => {}} profile={null} state="failed" failure="HTTP 503" />);

    expect(screen.getByRole("status", { name: "Volume profile" })).toHaveTextContent("Could not load the profile: HTTP 503");
  });

  it("says nothing of coverage while the profile is loading", () => {
    render(<ProfileControls window="24h" onWindow={() => {}} profile={null} state="loading" />);

    expect(screen.queryByText(/covers/)).toBeNull();
  });
});
