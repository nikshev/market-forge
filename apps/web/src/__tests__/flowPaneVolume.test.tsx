// @trace: REQ-WP-085
//
// The pane row with Volume in it: first, drawn from the bars as vertical bars, independent of the feature
// series, and "no data" only once the bars are known to be none.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FlowPane } from "../FlowPane";
import type { BarOut } from "../types";

const BASE = 1_788_838_800_000_000_000n;
const STEP = 900_000_000_000n;
const bar = (i: number, volume: string, isFinal = true): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "1",
  high: "1",
  low: "1",
  close: "1",
  volume_base: volume,
  is_final: isFinal,
});

describe("the volume pane", () => {
  it("is the first button in the row and the others keep their names", () => {
    render(
      <FlowPane
        points={[]}
        bars={[bar(0, "5")]}
        barsLoaded
        feature="volume"
        available={null}
        onSelect={() => {}}
      />,
    );

    const names = screen.getAllByRole("button").map((b) => b.textContent);
    expect(names[0]).toBe("Volume");
    expect(names).toContain("CVD");
    expect(names).toHaveLength(10);
    expect(screen.getByRole("button", { name: "Volume" })).toHaveAttribute("aria-pressed", "true");
  });

  it("draws one vertical bar per final bar and none for a forming one", () => {
    const { container } = render(
      <FlowPane
        points={[]}
        bars={[bar(0, "5"), bar(1, "0"), bar(2, "3"), bar(3, "9", false)]}
        barsLoaded
        feature="volume"
        available={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("img", { name: "volume over 3 point(s)" })).toBeInTheDocument();
    expect(container.querySelectorAll("svg rect")).toHaveLength(3);
  });

  it("is not hidden by a failed feature load, which belongs to the feature panes", () => {
    render(
      <FlowPane
        points={[]}
        bars={[bar(0, "5")]}
        barsLoaded
        feature="volume"
        available={null}
        failure="HTTP 503"
        onSelect={() => {}}
      />,
    );

    expect(screen.queryByRole("status", { name: "Pane load" })).toBeNull();
    expect(screen.getByRole("img", { name: /volume over 1 point/ })).toBeInTheDocument();
  });

  it("still shows the failure for a selected feature pane", () => {
    render(
      <FlowPane
        points={[]}
        bars={[bar(0, "5")]}
        barsLoaded
        feature="cvd"
        available={null}
        failure="HTTP 503"
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("status", { name: "Pane load" })).toHaveTextContent("HTTP 503");
  });

  it("is 'no data' and disabled once the bars are known to be none", () => {
    render(<FlowPane points={[]} bars={[]} barsLoaded feature={null} available={null} onSelect={() => {}} />);

    expect(screen.getByRole("button", { name: "Volume no data" })).toBeDisabled();
  });

  it("is not 'no data' while the bars are still unknown", () => {
    render(<FlowPane points={[]} bars={[]} feature="volume" available={null} onSelect={() => {}} />);

    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
  });

  it("is 'no data' when the only bars are still forming", () => {
    render(
      <FlowPane
        points={[]}
        bars={[bar(0, "5", false)]}
        barsLoaded
        feature={null}
        available={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("button", { name: "Volume no data" })).toBeDisabled();
  });
});
