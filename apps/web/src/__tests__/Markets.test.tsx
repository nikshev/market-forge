// @trace: REQ-WP-075
//
// The markets view: rows in the API's own order, unscored plainly unscored,
// and a row that is a link to the chart's deep link at the chosen timeframe.
//
// The assertions read the rendered anchors' `href`, which is the string the
// browser uses -- a click handler would need a router to be asserted against.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Markets } from "../Markets";
import { marketHref } from "../markets";
import { DEFAULT_TIMEFRAME } from "../timeframes";
import type { MarketOut } from "../types";

// Alphabetical order by symbol: AETHUSDT, BTCUSDT, ZECUSDT.
// The API's order is by rank, unscored last: ZECUSDT, ETHUSDT, AETHUSDT, BTCUSDT.
const MARKETS: MarketOut[] = [
  { venue: "okx", symbol: "ZECUSDT", market_type: "spot", setup_score: 0.9, rank_score: 0.9, confidence: 0.8 },
  { venue: "binance", symbol: "ETHUSDT", market_type: "perp", setup_score: 0.5, rank_score: 0.5, confidence: 0.6 },
  { venue: "binance", symbol: "AETHUSDT", market_type: "perp", setup_score: null, rank_score: null, confidence: null },
  { venue: "binance", symbol: "BTCUSDT", market_type: "perp", setup_score: null, rank_score: null, confidence: null },
];

const OFFERED = {
  timeframes: [
    { token: "1m", timeframe_ns: 60_000_000_000 },
    { token: "15m", timeframe_ns: 900_000_000_000 },
    { token: "1h", timeframe_ns: 3_600_000_000_000 },
  ],
};

interface HarnessOptions {
  markets?: unknown;
  marketsOk?: boolean;
  offered?: unknown;
  offeredOk?: boolean;
}

function harness(options: HarnessOptions = {}): string[] {
  const calls: string[] = [];
  const respond = (payload: unknown, ok = true) => ({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload,
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      if (url.includes("/api/v1/markets")) {
        return respond(options.markets ?? { markets: MARKETS }, options.marketsOk ?? true);
      }
      if (url.includes("/api/v1/timeframes")) {
        return respond(options.offered ?? OFFERED, options.offeredOk ?? true);
      }
      return respond({}, false);
    }),
  );
  return calls;
}

function rowTexts(): string[] {
  return screen
    .getAllByRole("listitem")
    .map((row) => within(row).getByRole("link").textContent ?? "");
}

async function rowsLoaded(): Promise<void> {
  await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(MARKETS.length));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("US1: the list is what the API returned", () => {
  it("renders one row per market, in the API's order, not sorted", async () => {
    harness();
    render(<Markets />);

    await rowsLoaded();

    expect(rowTexts()).toEqual(["ZECUSDT", "ETHUSDT", "AETHUSDT", "BTCUSDT"]);
  });

  it("shows an unscored market as unscored, never as zero", async () => {
    harness();
    render(<Markets />);
    await rowsLoaded();

    const row = screen.getByRole("link", { name: "AETHUSDT" }).closest("li")!;
    expect(row).toHaveTextContent("rank unscored");
    expect(row).toHaveTextContent("setup unscored");
    expect(row).toHaveTextContent("confidence unscored");
    expect(row).not.toHaveTextContent("0.00");
  });

  it("shows a scored market's value", async () => {
    harness();
    render(<Markets />);
    await rowsLoaded();

    const row = screen.getByRole("link", { name: "ZECUSDT" }).closest("li")!;
    expect(row).toHaveTextContent("rank 0.90");
  });

  it("states a failed read and renders no rows", async () => {
    harness({ marketsOk: false });
    render(<Markets />);

    await waitFor(() => expect(screen.getByText(/could not be loaded: HTTP 500/)).toBeVisible());
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });

  it("reads an empty list as empty, not as a failure", async () => {
    harness({ markets: { markets: [] } });
    render(<Markets />);

    await waitFor(() => expect(screen.getByText(/No markets/)).toBeVisible());
    expect(screen.queryByText(/could not be loaded/)).toBeNull();
  });
});

describe("US2: a row opens the chart at the chosen timeframe", () => {
  it("links to the default timeframe's deep link", async () => {
    harness();
    render(<Markets />);
    await rowsLoaded();

    const first = screen.getAllByRole("link")[0]!;
    expect(first).toHaveAttribute("href", marketHref("okx", "ZECUSDT", DEFAULT_TIMEFRAME));
  });

  it("carries a chosen timeframe into every row's link", async () => {
    harness();
    render(<Markets />);
    await rowsLoaded();
    await waitFor(() => expect(screen.getByRole("button", { name: "1h" })).toBeVisible());

    await userEvent.click(screen.getByRole("button", { name: "1h" }));

    await waitFor(() => {
      const first = screen.getAllByRole("link")[0]!;
      expect(first).toHaveAttribute("href", marketHref("okx", "ZECUSDT", "1h"));
    });
    const btc = screen.getByRole("link", { name: "BTCUSDT" });
    expect(btc).toHaveAttribute("href", marketHref("binance", "BTCUSDT", "1h"));
  });
});

describe("US4: the offered timeframes are the deployment's", () => {
  it("renders exactly the served options, unseen tokens included", async () => {
    harness({
      offered: {
        timeframes: [
          { token: "1m", timeframe_ns: 60_000_000_000 },
          { token: "2h", timeframe_ns: 7_200_000_000_000 },
          { token: "12h", timeframe_ns: 43_200_000_000_000 },
        ],
      },
    });
    render(<Markets />);
    await rowsLoaded();

    const control = await screen.findByRole("region", { name: "Timeframe" });
    expect(within(control).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "1m",
      "2h",
      "12h",
    ]);
  });

  it("states a failed offered read, keeps the rows, and links at the default", async () => {
    harness({ offeredOk: false });
    render(<Markets />);
    await rowsLoaded();

    await waitFor(() => expect(screen.getByText(/could not be loaded: HTTP 500/)).toBeVisible());
    // No options at all: a hard-coded fallback would render here.
    expect(screen.queryByRole("region", { name: "Timeframe" })).toBeNull();
    for (const link of screen.getAllByRole("link")) {
      expect(link.getAttribute("href")).toContain(`tf=${DEFAULT_TIMEFRAME}`);
    }
  });
});
