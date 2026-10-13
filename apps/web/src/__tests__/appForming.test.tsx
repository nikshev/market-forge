// @trace: REQ-WP-106
//
// On a timeframe above one minute the chart's last candle is the window in progress, built from the minutes, with the current price as
// its close: stored 1m bars from the first window the table has not got, then the live ones after them.

import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BarOut } from "../types";

const MIN = 60_000_000_000n;
const HOUR = 60n * MIN;
const FOUR_H = 4n * HOUR;
const T0 = 1_789_344_000_000_000_000n - (1_789_344_000_000_000_000n % FOUR_H);

const seen = vi.hoisted(() => ({
  chart: [] as { bars: BarOut[]; liveBars: readonly BarOut[] | undefined }[],
  pane: [] as { liveBars: readonly BarOut[] | undefined }[],
  live: { bars: [] as BarOut[], status: "live" as "live" | "delayed" | "off" },
  calls: [] as string[],
}));

vi.mock("../useLiveBars", () => ({
  useLiveBars: (args: { enabled: boolean }) => (args.enabled ? seen.live : { bars: [], status: "off" }),
}));
vi.mock("../Chart", () => ({
  Chart: (props: { bars: BarOut[]; liveBars?: readonly BarOut[] }) => {
    seen.chart.push({ bars: props.bars, liveBars: props.liveBars });
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

const wire = (open: bigint, tf: bigint, close = "100") => ({
  open_time_ns: String(open),
  close_time_ns: String(open + tf),
  open: "100",
  high: "101",
  low: "99",
  close,
  volume_base: "1",
  is_final: true,
});
const live = (minute: number, close: string): BarOut => ({
  open_time_ns: T0 + FOUR_H + BigInt(minute) * MIN,
  close_time_ns: T0 + FOUR_H + BigInt(minute + 1) * MIN,
  open: "100",
  high: "101",
  low: "99",
  close,
  volume_base: "1",
  is_final: false,
});

beforeEach(() => {
  seen.chart.length = 0;
  seen.pane.length = 0;
  seen.calls.length = 0;
  seen.live = { bars: [live(60, "333")], status: "live" };
  window.history.replaceState(null, "", "/chart/bybit/BTCUSDT?tf=4h");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const u = String(url);
      seen.calls.push(u);
      const body = u.includes("/api/v1/timeframes")
        ? {
            timeframes: [
              { token: "1m", timeframe_ns: 60_000_000_000 },
              { token: "4h", timeframe_ns: Number(FOUR_H) },
            ],
          }
        : u.includes("/api/v1/bars") && u.includes("timeframe_ns=60000000000")
          ? { bars: [wire(T0 + FOUR_H, MIN, "222"), wire(T0 + FOUR_H + MIN, MIN, "223")] }
          : u.includes("/api/v1/bars")
            ? { bars: [wire(T0, FOUR_H)] }
            : u.includes("/extrema")
              ? { confirmed: [], candidates: [] }
              : u.includes("/timeseries")
                ? { points: [] }
                : {};
      return { ok: !u.includes("/channels") && !u.includes("/dex/"), status: 200, json: async () => body };
    }),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the chart's last candle on a longer timeframe", () => {
  it("is the window in progress, with the live price as its close, handed to the chart and to the pane", async () => {
    render(<App />);

    await waitFor(() => {
      const last = seen.chart.at(-1)?.liveBars;
      expect(last).toHaveLength(1);
      expect(last![0]).toMatchObject({
        open_time_ns: T0 + FOUR_H,
        close_time_ns: T0 + 2n * FOUR_H,
        close: "333",
        is_final: false,
      });
    });
    expect(seen.pane.at(-1)?.liveBars).toEqual(seen.chart.at(-1)?.liveBars);
  });

  it("asks the table for the minutes from the first window it has not got, at one minute", async () => {
    render(<App />);

    await waitFor(() => expect(seen.calls.some((u) => u.includes("timeframe_ns=60000000000"))).toBe(true));
    const url = seen.calls.find((u) => u.includes("timeframe_ns=60000000000"))!;
    expect(url).toContain(`start_ns=${T0 + FOUR_H + MIN}`);
    expect(url).toContain("limit=10000");
  });

  it("includes the stored minutes of the window, not only the live ones: the high and low are the window's", async () => {
    seen.live = { bars: [live(60, "333")], status: "live" };
    render(<App />);

    await waitFor(() => {
      const bar = seen.chart.at(-1)?.liveBars?.[0];
      expect(bar?.open).toBe("100");
      expect(Number(bar?.volume_base)).toBe(3); // two stored minutes and one live
    });
  });

  it("builds the window from the stored minutes alone when the feed is down -- as current as the table is -- and the chip says delayed", async () => {
    seen.live = { bars: [], status: "delayed" };
    render(<App />);

    await waitFor(() => {
      const bar = seen.chart.at(-1)?.liveBars?.[0];
      expect(bar).toMatchObject({ open_time_ns: T0 + FOUR_H, close: "223", is_final: false });
    });
  });

  it("passes the minutes straight through on the one-minute chart, and asks for no extra minutes", async () => {
    window.history.replaceState(null, "", "/chart/bybit/BTCUSDT?tf=1m");
    render(<App />);

    await waitFor(() => expect(seen.chart.at(-1)?.liveBars).toEqual([live(60, "333")]));
    expect(seen.calls.filter((u) => u.includes("/api/v1/bars"))).toHaveLength(1);
  });
});
