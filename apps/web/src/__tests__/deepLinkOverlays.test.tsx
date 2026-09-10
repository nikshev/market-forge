// @trace: REQ-US-002

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { parseDeepLink } from "../deepLink";
import { NOT_RECORDED, RESTORED, UNREADABLE } from "../overlays";

// The chart is stubbed, not rendered. jsdom has no layout engine, so
// `lightweight-charts` cannot measure a container -- the note in `test-setup.ts`
// is about exactly this. What these tests check is what the reader is told
// about the restoration, which is above the chart, not inside it.
vi.mock("../Chart", () => ({ Chart: () => <div data-testid="chart" /> }));

vi.mock("../api", () => ({
  fetchBars: async () => ({ ok: true, value: { bars: [] } }),
  fetchChannel: async () => ({ ok: false, error: "no channel" }),
}));

describe("the deep link's overlays", () => {
  it("carries the link's layers through to the page", () => {
    // SC-004. The parse is what the chart is handed.
    const link = parseDeepLink(
      "/chart/binance/BTCUSDT",
      "?tf=15m&at=2026-09-07T09:00:00Z&overlays=candles,vwap",
    );

    expect(link?.overlays.state).toBe(RESTORED);
    expect(link?.overlays.overlays).toEqual(["candles", "vwap"]);
  });

  it("marks a link without the parameter as not recorded", () => {
    const link = parseDeepLink("/chart/binance/BTCUSDT", "?tf=15m");

    expect(link?.overlays.state).toBe(NOT_RECORDED);
  });

  it("marks an unreadable list as unreadable", () => {
    const link = parseDeepLink("/chart/binance/BTCUSDT", "?tf=15m&overlays=candles,teleporter");

    expect(link?.overlays.state).toBe(UNREADABLE);
  });

  it("tells the reader when the alert's own layers were not restored", async () => {
    // SC-005, FR-005. A page that silently showed its defaults would claim to
    // have restored a state nobody recorded -- the same failure ADR-020 is
    // about, one parameter over.
    window.history.pushState({}, "", "/chart/binance/BTCUSDT?tf=15m");

    render(<App />);

    expect(
      await screen.findByRole("status", { name: "Overlay restoration" }),
    ).toHaveTextContent(/did not record which layers/);
  });

  it("says nothing when the layers were restored", async () => {
    window.history.pushState({}, "", "/chart/binance/BTCUSDT?tf=15m&overlays=candles");

    render(<App />);

    // By name rather than by being the only status on the page. The lower pane
    // ([[REQ-WP-027]]) has its own, and a test that asserted "no status at all"
    // would fail for a reason that has nothing to do with overlays.
    expect(screen.queryByRole("status", { name: "Overlay restoration" })).toBeNull();
  });
});
