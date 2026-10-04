// @trace: REQ-WP-092

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../PaneChart", () => ({
  PaneChart: ({ feature }: { feature: string }) => <div data-testid="pane-chart" data-feature={feature} />,
}));

import { FlowPane } from "../FlowPane";
import type { BarOut, FeaturePointOut } from "../types";

const STEP = 60_000_000_000n;
const BASE = 1_788_838_800_000_000_000n;
const bar = (i: number): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: String(i + 1),
  is_final: true,
});
const handle = { api: {} as never, candles: () => null };
const points: FeaturePointOut[] = [{ at_ns: BASE + STEP, values: { ofi_1m: 1 } }];

describe("the pane with and without the main chart's handle", () => {
  it("draws the pane chart for Volume when it has the handle, and not the SVG", () => {
    const { container } = render(
      <FlowPane points={[]} bars={[bar(0), bar(1)]} barsLoaded feature="volume" available={null} chart={handle} onSelect={() => {}} />,
    );

    expect(screen.getByTestId("pane-chart")).toHaveAttribute("data-feature", "volume");
    expect(container.querySelector("svg")).toBeNull();
  });

  it("draws the pane chart for a feature pane that has data", () => {
    render(
      <FlowPane points={points} bars={[bar(0)]} barsLoaded feature="ofi_1m" available={new Set(["ofi_1m"])} chart={handle} onSelect={() => {}} />,
    );

    expect(screen.getByTestId("pane-chart")).toHaveAttribute("data-feature", "ofi_1m");
  });

  it("falls back to the SVG without a handle, so a missing chart is never an empty pane", () => {
    render(
      <FlowPane points={[]} bars={[bar(0), bar(1)]} barsLoaded feature="volume" available={null} onSelect={() => {}} />,
    );

    expect(screen.queryByTestId("pane-chart")).toBeNull();
    expect(screen.getByRole("img", { name: "volume over 2 point(s)" })).toBeInTheDocument();
  });

  it("falls back to the SVG when the handle is null", () => {
    render(
      <FlowPane points={[]} bars={[bar(0)]} barsLoaded feature="volume" available={null} chart={null} onSelect={() => {}} />,
    );

    expect(screen.getByRole("img", { name: /volume over 1 point/ })).toBeInTheDocument();
  });

  it("draws no chart for a pane with nothing to show, and says why as before", () => {
    render(
      <FlowPane points={[]} bars={[]} barsLoaded feature="volume" available={null} chart={handle} onSelect={() => {}} />,
    );

    expect(screen.queryByTestId("pane-chart")).toBeNull();
    expect(screen.getByRole("status", { name: "Pane contents" })).toBeInTheDocument();
  });

  it("keeps the pane's buttons and their names", () => {
    render(
      <FlowPane points={points} bars={[bar(0)]} barsLoaded feature="volume" available={new Set(["volume", "ofi_1m"])} chart={handle} onSelect={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "Volume" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "OFI (1m)" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "CVD (base) no data" })).toBeDisabled();
  });
});
