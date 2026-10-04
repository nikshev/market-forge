// @trace: REQ-WP-083
//
// The overview as cards. The accessible contract is the one the existing tests assert and these keep: a list
// named "Markets" whose items are links named by their symbol, a timeframe group with one pressed button.
// What is new is what a reader sees: the venue, a market-type chip that tells spot from perp, and scores
// shown as absent.

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketTypeChip } from "../MarketTypeChip";
import { Markets } from "../Markets";

const MARKETS = [
  { venue: "binance", symbol: "BTCUSDT", market_type: "spot" },
  { venue: "binance", symbol: "ETHUSDT", market_type: "spot" },
  { venue: "bybit", symbol: "BTCUSDT", market_type: "perp" },
  { venue: "okx", symbol: "BTC-USDT-SWAP", market_type: "perp" },
].map((m) => ({ ...m, setup_score: null, rank_score: null, confidence: null }));

const TIMEFRAMES = {
  timeframes: [
    { token: "1m", timeframe_ns: 60_000_000_000 },
    { token: "15m", timeframe_ns: 900_000_000_000 },
  ],
};

function respond(markets: unknown[] = MARKETS): void {
  vi.stubGlobal("fetch", async (url: string) => {
    const body = String(url).includes("/timeframes") ? TIMEFRAMES : { markets };
    return new Response(JSON.stringify(body), { status: 200 });
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("the overview as cards", () => {
  it("lists one card per market in a list named Markets", async () => {
    respond();

    render(<Markets />);

    const list = await screen.findByRole("list", { name: "Markets" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(4);
  });

  it("each card is a link whose accessible name is exactly the symbol", async () => {
    respond();

    render(<Markets />);

    const links = await screen.findAllByRole("link", { name: "BTCUSDT" });
    expect(links).toHaveLength(2);
    expect(links[0].getAttribute("href")).toMatch(/^\/chart\/binance\/BTCUSDT\?/);
    expect(screen.getByRole("link", { name: "BTC-USDT-SWAP" })).toBeInTheDocument();
  });

  it("shows each market's venue on its card", async () => {
    respond();

    render(<Markets />);

    const list = await screen.findByRole("list", { name: "Markets" });
    expect(within(list).getAllByText("binance")).toHaveLength(2);
    expect(within(list).getByText("bybit")).toBeInTheDocument();
    expect(within(list).getByText("okx")).toBeInTheDocument();
  });

  it("shows a spot chip and a perp chip that differ in text and in colour", async () => {
    respond();

    render(<Markets />);

    const list = await screen.findByRole("list", { name: "Markets" });
    const spot = within(list).getAllByText("spot")[0].closest(".MuiChip-root");
    const perp = within(list).getAllByText("perp")[0].closest(".MuiChip-root");
    expect(spot?.className).toContain("MuiChip-colorInfo");
    expect(perp?.className).toContain("MuiChip-colorWarning");
    expect(spot?.className).not.toEqual(perp?.className);
  });

  it("shows absent scores as unscored, and de-emphasised rather than as zero", async () => {
    respond();

    render(<Markets />);

    const list = await screen.findByRole("list", { name: "Markets" });
    const chips = within(list).getAllByText(/unscored/);
    expect(chips.length).toBe(4 * 3);
    for (const chip of chips) {
      expect(chip.closest(".MuiChip-root")?.className).toContain("MuiChip-outlined");
    }
    expect(within(list).queryByText(/\b0\b/)).toBeNull();
  });

  it("says so, as a status, when there are no markets", async () => {
    respond([]);

    render(<Markets />);

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("No markets are configured on this deployment.");
  });

  it("presses the chosen timeframe and only it", async () => {
    respond();

    render(<Markets />);

    // 15m is the default timeframe (`DEFAULT_TIMEFRAME`); the other offered one is not pressed.
    expect(await screen.findByRole("button", { name: "15m", pressed: true })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1m", pressed: false })).toBeInTheDocument();
  });

  it("has a heading Markets under the page's single level-one heading", async () => {
    respond();

    render(<Markets />);

    expect(await screen.findByRole("heading", { name: "Markets", level: 2 })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

describe("MarketTypeChip", () => {
  it("renders the type as its text", () => {
    render(<MarketTypeChip type="perp" />);

    expect(screen.getByText("perp")).toBeInTheDocument();
  });

  it("renders a type it does not know without a colour, and without throwing", () => {
    const { container } = render(<MarketTypeChip type="option" />);

    expect(screen.getByText("option")).toBeInTheDocument();
    expect(container.querySelector(".MuiChip-colorInfo, .MuiChip-colorWarning")).toBeNull();
  });
});
