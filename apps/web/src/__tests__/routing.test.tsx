// @trace: REQ-WP-075
//
// Which path renders what. The root and /markets are the markets view; an
// unknown path keeps the placeholder that says where a chart can be opened
// -- a silent redirect would hide a mistyped URL; /chart keeps its route.

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

vi.mock("../Chart", () => ({
  Chart: () => <div data-testid="chart" />,
}));

const OFFERED = {
  timeframes: [{ token: "15m", timeframe_ns: 900_000_000_000 }],
};

const MARKETS = {
  markets: [
    {
      venue: "binance",
      symbol: "BTCUSDT",
      market_type: "perp",
      setup_score: null,
      rank_score: null,
      confidence: null,
    },
  ],
};

function stubFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/api/v1/markets")) {
        return { ok: true, status: 200, json: async () => MARKETS };
      }
      if (url.includes("/api/v1/timeframes")) {
        return { ok: true, status: 200, json: async () => OFFERED };
      }
      if (url.includes("/api/v1/bars")) {
        return { ok: true, status: 200, json: async () => ({ bars: [] }) };
      }
      if (url.includes("/api/v1/features/timeseries")) {
        return { ok: true, status: 200, json: async () => ({ points: [] }) };
      }
      if (url.includes("/api/v1/extrema")) {
        return { ok: true, status: 200, json: async () => ({ confirmed: [], candidates: [] }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }),
  );
}

function openAt(pathname: string): void {
  window.history.replaceState(null, "", pathname);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("which path renders what", () => {
  it("serves the markets view at the root", async () => {
    openAt("/");
    stubFetch();

    render(<App />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Markets" })).toBeVisible());
    expect(screen.getByRole("link", { name: "BTCUSDT" })).toBeVisible();
  });

  it("serves the markets view at /markets", async () => {
    openAt("/markets");
    stubFetch();

    render(<App />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Markets" })).toBeVisible());
  });

  it("keeps the placeholder for an unknown path, naming where a chart opens", () => {
    openAt("/nonsense");
    stubFetch();

    render(<App />);

    expect(screen.getByText(/Open a chart at \/chart/)).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Markets" })).toBeNull();
  });

  it("leaves the chart route exactly as it was", async () => {
    openAt("/chart/binance/BTCUSDT");
    stubFetch();

    render(<App />);

    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("BTCUSDT"),
    );
    expect(screen.queryByRole("heading", { name: "Markets" })).toBeNull();
  });
});
