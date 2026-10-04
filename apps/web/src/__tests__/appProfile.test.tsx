// @trace: REQ-WP-089
//
// The page and the volume profile: it asks for the profile of the market in the link, in the window pressed, as of the
// link's instant; it says "collecting" for a 404 and a failure for a failure; and none of it holds up the chart.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { VolumeProfileOut } from "../types";

const api = vi.hoisted(() => ({
  fetchVolumeProfile: vi.fn(),
}));

vi.mock("../api", () => ({
  fetchBars: async () => ({ ok: true, value: { bars: [] } }),
  fetchChannel: async () => ({ ok: false, error: "HTTP 404" }),
  fetchDexDepth: async () => ({ ok: false, error: "HTTP 404" }),
  fetchExtrema: async () => ({ ok: true, value: { confirmed: [], candidates: [] } }),
  fetchFeatureSeries: async () => ({ ok: true, value: { points: [] } }),
  fetchTimeframes: async () => ({ ok: true, value: { timeframes: [{ token: "15m", timeframe_ns: 900_000_000_000 }] } }),
  fetchVolumeProfile: api.fetchVolumeProfile,
}));
vi.mock("../Chart", () => ({ Chart: () => null }));

import { App } from "../App";

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

function open(search = ""): void {
  window.history.pushState({}, "", `/chart/binance/BTCUSDT${search}`);
}

beforeEach(() => {
  api.fetchVolumeProfile.mockReset();
});

describe("the page and the volume profile", () => {
  it("asks for the market in the link, 24h by default, with no instant when the link has none", async () => {
    api.fetchVolumeProfile.mockResolvedValue({ ok: true, value: profile() });
    open();

    render(<App />);

    await waitFor(() => expect(api.fetchVolumeProfile).toHaveBeenCalled());
    expect(api.fetchVolumeProfile).toHaveBeenCalledWith({
      venue: "binance",
      symbol: "BTCUSDT",
      window: "24h",
      atNs: null,
    });
    expect(await screen.findByText("covers 3 h 20 m of 24 h")).toBeInTheDocument();
  });

  it("asks again for the window that is pressed", async () => {
    api.fetchVolumeProfile.mockResolvedValue({ ok: true, value: profile() });
    open();
    render(<App />);
    await screen.findByText("covers 3 h 20 m of 24 h");

    fireEvent.click(screen.getByRole("button", { name: "4h profile" }));

    await waitFor(() =>
      expect(api.fetchVolumeProfile).toHaveBeenLastCalledWith(expect.objectContaining({ window: "4h" })),
    );
  });

  it("says nothing has been collected for a 404, and a failure for any other error", async () => {
    api.fetchVolumeProfile.mockResolvedValue({ ok: false, error: "HTTP 404" });
    open();
    const first = render(<App />);
    expect(await screen.findByText("no price bins collected for this market yet")).toBeInTheDocument();
    first.unmount();

    api.fetchVolumeProfile.mockResolvedValue({ ok: false, error: "HTTP 503" });
    render(<App />);
    expect(await screen.findByText("Could not load the profile: HTTP 503")).toBeInTheDocument();
  });

  it("states a profile call that throws as a failure and leaves the page standing", async () => {
    api.fetchVolumeProfile.mockRejectedValue(new Error("boom"));
    open();

    render(<App />);

    expect(await screen.findByText("Could not load the profile: boom")).toBeInTheDocument();
  });

  it("does not ask for a profile when the link has the layer off", async () => {
    open("?overlays=candles");

    render(<App />);
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(api.fetchVolumeProfile).not.toHaveBeenCalled();
    expect(screen.queryByRole("group", { name: "Profile window" })).toBeNull();
  });
});
