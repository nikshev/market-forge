// @trace: REQ-WP-081
//
// The overview with what the stack really lists once each ingest service has registered its market: five
// markets, binance spot and bybit and okx perp, scores absent. The page was not changed; this pins that it
// renders that shape, because an empty list was the first thing a phone would have shown.

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Markets } from "../Markets";

const MARKETS = [
  { venue: "binance", symbol: "BTCUSDT", market_type: "spot" },
  { venue: "binance", symbol: "ETHUSDT", market_type: "spot" },
  { venue: "binance", symbol: "SOLUSDT", market_type: "spot" },
  { venue: "bybit", symbol: "BTCUSDT", market_type: "perp" },
  { venue: "okx", symbol: "BTC-USDT-SWAP", market_type: "perp" },
].map((market) => ({ ...market, setup_score: null, rank_score: null, confidence: null }));

const TIMEFRAMES = {
  timeframes: [
    { token: "1m", timeframe_ns: 60_000_000_000 },
    { token: "15m", timeframe_ns: 900_000_000_000 },
  ],
};

function respond(): void {
  vi.stubGlobal("fetch", async (url: string) => {
    const body = String(url).includes("/timeframes") ? TIMEFRAMES : { markets: MARKETS };
    return new Response(JSON.stringify(body), { status: 200 });
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the overview with five registered markets", () => {
  it("lists five rows, each a link to its chart", async () => {
    respond();

    render(<Markets />);

    const list = await screen.findByRole("list", { name: "Markets" });
    await waitFor(() => expect(list.querySelectorAll("li")).toHaveLength(5));
    const links = Array.from(list.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    expect(links).toHaveLength(5);
    for (const href of links) {
      expect(href).toMatch(/^\/chart\/(binance|bybit|okx)\/[A-Z0-9-]+\?/);
    }
  });

  it("says each market's venue and type, spot for Binance and perp for the others", async () => {
    respond();

    render(<Markets />);

    await screen.findByRole("list", { name: "Markets" });
    expect(screen.getAllByText(/binance · spot/)).toHaveLength(3);
    expect(screen.getByText(/bybit · perp/)).toBeInTheDocument();
    expect(screen.getByText(/okx · perp/)).toBeInTheDocument();
  });

  it("shows absent scores as absent and says nothing about an empty list", async () => {
    respond();

    render(<Markets />);

    await screen.findByRole("list", { name: "Markets" });
    expect(screen.queryByText(/No markets are configured/)).toBeNull();
    expect(screen.getAllByText(/rank/).length).toBe(5);
  });
});
