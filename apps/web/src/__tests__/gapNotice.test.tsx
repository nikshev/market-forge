// @trace: REQ-WP-086

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GapNotice } from "../GapNotice";
import type { BarOut } from "../types";

const STEP = 3_600_000_000_000n;
const BASE = BigInt(Date.UTC(2026, 8, 26, 6, 0, 0)) * 1_000_000n; // 26.09 06:00 UTC
const bar = (i: number): BarOut => ({
  open_time_ns: BASE + BigInt(i) * STEP,
  close_time_ns: BASE + BigInt(i + 1) * STEP,
  open: "1",
  high: "1",
  low: "1",
  close: "1",
  volume_base: "1",
  is_final: true,
});

describe("the notice under the chart", () => {
  it("lists each hole with how many bars are missing and the span, in a status named for it", () => {
    render(<GapNotice bars={[bar(0), bar(1), bar(150), bar(151)]} />);

    const notice = screen.getByRole("status", { name: "Gaps in the bars" });
    expect(notice).toHaveTextContent("148 bars missing, 26.09 08:00 to 02.10 12:00");
  });

  it("is absent when there is no hole", () => {
    render(<GapNotice bars={[bar(0), bar(1), bar(2)]} />);

    expect(screen.queryByRole("status", { name: "Gaps in the bars" })).toBeNull();
  });

  it("caps its list at five and counts the rest", () => {
    const indices = Array.from({ length: 8 }, (_, i) => i * 3);

    render(<GapNotice bars={indices.map(bar)} />);

    const notice = screen.getByRole("status", { name: "Gaps in the bars" });
    expect(notice).toHaveTextContent("and 2 more");
    expect(notice.querySelectorAll("li")).toHaveLength(5);
  });
});
