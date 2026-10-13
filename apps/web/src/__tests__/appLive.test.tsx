// @trace: REQ-WP-102
//
// The page's side of the live feed: it asks for the socket only for the 1m chart of a live (not pinned) view, hands the bars it
// hears to the chart and to the pane under it, and says whether the chart is live or delayed.

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const seen = vi.hoisted(() => ({
  hook: [] as { venue: string; symbol: string; enabled: boolean }[],
  chart: [] as { liveBars: readonly BarOut[] | undefined }[],
  pane: [] as { liveBars: readonly BarOut[] | undefined }[],
  result: { bars: [] as BarOut[], status: "live" as "live" | "delayed" | "off" },
}));

vi.mock("../useLiveBars", () => ({
  useLiveBars: (args: { venue: string; symbol: string; enabled: boolean }) => {
    seen.hook.push(args);
    return args.enabled ? seen.result : { bars: [], status: "off" };
  },
}));
vi.mock("../Chart", () => ({
  Chart: (props: { liveBars?: readonly BarOut[] }) => {
    seen.chart.push({ liveBars: props.liveBars });
    return <div data-testid="chart" />;
  },
}));
vi.mock("../FlowPane", () => ({
  FlowPane: (props: { liveBars?: readonly BarOut[] }) => {
    seen.pane.push({ liveBars: props.liveBars });
    return <div data-testid="flow-pane" />;
  },
}));

import { App } from "../App";

const MIN = 60_000_000_000;
const OFFERED = {
  timeframes: [
    { token: "1m", timeframe_ns: MIN },
    { token: "5m", timeframe_ns: 5 * MIN },
  ],
};
const live = (minute: number): BarOut => ({
  open_time_ns: 1_789_344_000_000_000_000n + BigInt(minute * MIN),
  close_time_ns: 1_789_344_000_000_000_000n + BigInt((minute + 1) * MIN),
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: "1",
  is_final: false,
});

function open(search: string): void {
  window.history.replaceState(null, "", `/chart/bybit/BTCUSDT${search}`);
}

beforeEach(() => {
  seen.hook.length = 0;
  seen.chart.length = 0;
  seen.pane.length = 0;
  seen.result = { bars: [live(5), live(6)], status: "live" };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: !url.includes("/channels") && !url.includes("/dex/"),
      status: 200,
      json: async () =>
        url.includes("/api/v1/timeframes")
          ? OFFERED
          : url.includes("/api/v1/bars")
            ? {
                bars: [
                  {
                    open_time_ns: "1789344000000000000",
                    close_time_ns: "1789344060000000000",
                    open: "100",
                    high: "100",
                    low: "100",
                    close: "100",
                    volume_base: "1",
                    is_final: true,
                  },
                ],
              }
            : url.includes("/extrema")
              ? { confirmed: [], candidates: [] }
              : url.includes("/timeseries")
                ? { points: [] }
                : {},
    })),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
});

const enabledCalls = () => seen.hook.filter((h) => h.enabled);

describe("the live feed on the page", () => {
  it("is asked for on every timeframe of this series, since the minutes build the longer windows too (REQ-WP-106)", async () => {
    open("?tf=1m");
    const { unmount } = render(<App />);
    await waitFor(() => expect(enabledCalls().length).toBeGreaterThan(0));
    expect(enabledCalls().at(-1)).toMatchObject({ venue: "bybit", symbol: "BTCUSDT", enabled: true });
    unmount();

    seen.hook.length = 0;
    open("?tf=5m");
    render(<App />);
    await waitFor(() => expect(enabledCalls().length).toBeGreaterThan(0));
    expect(enabledCalls().at(-1)).toMatchObject({ venue: "bybit", symbol: "BTCUSDT", enabled: true });
  });

  it("is not asked for when the view is pinned to an instant", async () => {
    open("?tf=1m&at=2026-01-01T00:00:00Z");
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("chart")).toBeInTheDocument());

    expect(enabledCalls()).toHaveLength(0);
  });

  it("hands the bars it hears to the chart and to the pane under it", async () => {
    open("?tf=1m");
    render(<App />);

    await waitFor(() => expect(seen.chart.at(-1)?.liveBars).toEqual([live(5), live(6)]));
    await waitFor(() => expect(seen.pane.at(-1)?.liveBars).toEqual([live(5), live(6)]));
  });

  it("says live while the feed is live", async () => {
    open("?tf=1m");
    render(<App />);

    expect(await screen.findByRole("status", { name: "Live feed" })).toHaveTextContent(/live/i);
    expect(screen.getByRole("status", { name: "Live feed" })).not.toHaveTextContent(/delayed/i);
  });

  it("says delayed, and why, while the feed is not connected", async () => {
    seen.result = { bars: [], status: "delayed" };
    open("?tf=1m");
    render(<App />);

    const chip = await screen.findByRole("status", { name: "Live feed" });
    expect(chip).toHaveTextContent(/delayed/i);
    expect(chip).toHaveAttribute("title", expect.stringMatching(/reloads/i));
  });

  it("says nothing about the feed for a view pinned to an instant, which is history", async () => {
    open("?tf=1m&at=2026-01-01T00:00:00Z");
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("chart")).toBeInTheDocument());

    expect(screen.queryByRole("status", { name: "Live feed" })).toBeNull();
  });
});
