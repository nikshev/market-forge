// @trace: REQ-WP-084
//
// The page, with its API replaced: what the pane row says before the feature series has answered, when it
// failed, and after it answered with a series that carries only some features. The chart is stubbed (jsdom
// cannot lay it out); what is under test is the pane row and the selection.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FeatureSeriesResponse } from "../types";

const api = vi.hoisted(() => ({
  series: null as null | (() => Promise<unknown>),
}));

vi.mock("../Chart", () => ({ Chart: () => <div data-testid="chart" /> }));
vi.mock("../api", () => ({
  fetchTimeframes: async () => ({
    ok: true,
    value: {
      timeframes: [
        { token: "5m", timeframe_ns: 300_000_000_000 },
        { token: "15m", timeframe_ns: 900_000_000_000 },
      ],
    },
  }),
  fetchBars: async () => ({
    ok: true,
    value: {
      bars: [
        {
          open_time_ns: 1788838800000000000n,
          close_time_ns: 1788839700000000000n,
          open: "100",
          high: "101",
          low: "99",
          close: "100",
          volume_base: "1",
          is_final: true,
        },
      ],
    },
  }),
  fetchChannel: async () => ({ ok: false, error: "no channel" }),
  fetchExtrema: async () => ({ ok: true, value: { confirmed: [], candidates: [] } }),
  fetchDexDepth: async () => ({ ok: false, error: "none" }),
  fetchFeatureSeries: () => api.series?.(),
}));

import { App } from "../App";

const series = (values: Record<string, number>[]): { ok: true; value: FeatureSeriesResponse } => ({
  ok: true,
  value: {
    points: values.map((v, i) => ({ at_ns: 1788838800000000000n + BigInt(i) * 1_000_000_000n, values: v })),
  },
});

function open(): void {
  window.history.pushState({}, "", "/chart/binance/BTCUSDT?tf=15m");
}

describe("the pane row on the chart page", () => {
  beforeEach(() => {
    open();
  });

  it("claims nothing of any pane before the feature series has answered", async () => {
    let release: (value: unknown) => void = () => {};
    api.series = () => new Promise((resolve) => (release = resolve));

    render(<App />);

    expect(await screen.findByRole("group", { name: "Pane" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();

    release(series([{ ofi_1m: 1 }]));
    await waitFor(() => expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(8));
  });

  it("claims nothing of any pane when the feature load failed, and says it failed", async () => {
    api.series = async () => ({ ok: false, error: "HTTP 503" });

    render(<App />);

    expect(await screen.findByRole("status", { name: "Pane load" })).toHaveTextContent("HTTP 503");
    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
  });

  it("offers one pane and eight 'no data' when the series carries only OFI, and selects the one", async () => {
    api.series = async () => series([{ ofi_1m: 1 }, { ofi_1m: 2 }]);

    render(<App />);

    const live = await screen.findByRole("button", { name: "OFI (1m)" });
    await waitFor(() => expect(live).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(8);
  });

  it("says every pane has no data, and that no pane has any, for an empty series", async () => {
    api.series = async () => series([]);

    render(<App />);

    await waitFor(() => expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(9));
    expect(screen.getByRole("status", { name: "Pane contents" })).toHaveTextContent(
      "No pane has data for this view",
    );
  });

  it("does not take a valid choice away when the same data is fetched again", async () => {
    api.series = async () => series([{ ofi_1m: 1, funding_z: 2 }]);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Funding (z)" }));
    expect(screen.getByRole("button", { name: "Funding (z)" })).toHaveAttribute("aria-pressed", "true");

    // A timeframe round trip fetches everything again.
    fireEvent.click(await screen.findByRole("button", { name: "5m" }));
    fireEvent.click(await screen.findByRole("button", { name: "15m" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Funding (z)" })).toHaveAttribute("aria-pressed", "true"),
    );
  });

  it("offers the candidate switch, off, whatever the API returned", async () => {
    api.series = async () => series([]);

    render(<App />);

    expect(await screen.findByRole("button", { name: "Candidate extrema" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});
