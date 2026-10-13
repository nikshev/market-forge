// @trace: REQ-WP-090
//
// Timer, pinned, hidden, in-flight, failure recovery for live refresh

import { render, screen, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

vi.mock("../Chart", () => ({
  Chart: () => <div data-testid="chart" />,
}));

const MINUTE_NS = 60_000_000_000;

const OFFERED = {
  timeframes: [
    { token: "1m", timeframe_ns: MINUTE_NS },
    { token: "5m", timeframe_ns: 5 * MINUTE_NS },
    { token: "15m", timeframe_ns: 15 * MINUTE_NS },
    { token: "30m", timeframe_ns: 30 * MINUTE_NS },
    { token: "1h", timeframe_ns: 60 * MINUTE_NS },
    { token: "4h", timeframe_ns: 240 * MINUTE_NS },
  ],
};

function barPayload(openNs = 1_789_344_000_000_000_000n, close = "100", isFinal = true) {
  return {
    open_time_ns: String(openNs),
    close_time_ns: String(openNs + BigInt(MINUTE_NS)),
    open: close,
    high: close,
    low: close,
    close,
    volume_base: "1",
    is_final: isFinal,
  };
}

function openAt(search: string): void {
  window.history.replaceState(null, "", `/chart/binance/BTCUSDT${search}`);
}

// The minutes a longer timeframe's window in progress is built from (REQ-WP-106) are asked for beside the series, at one minute and
// with the largest limit; they are not "the chart's bars", which is what these tests count.
const isMinuteBuild = (url: string): boolean => url.includes("timeframe_ns=60000000000") && url.includes("limit=10000");

function seriesCalls(calls: string[], path: string): string[] {
  return calls.filter((url) => url.includes(path) && !isMinuteBuild(url));
}

function lastSeriesCall(calls: string[], path: string): string | undefined {
  return seriesCalls(calls, path).at(-1);
}

function makeHarness(options: { barsFail?: boolean; deferBars?: boolean } = {}) {
  const calls: string[] = [];
  const pending: (() => void)[] = [];
  let barsCalls = 0;
  const { barsFail = false, deferBars = false } = options;

  const respond = (payload: unknown, ok = true) => ({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload,
  });

  vi.useFakeTimers({ shouldAdvanceTime: true });

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      if (url.includes("/api/v1/timeframes")) {
        return respond(OFFERED, true);
      }
      if (url.includes("/api/v1/bars")) {
        barsCalls += 1;
        if (deferBars && barsCalls === 1) {
          const gate = new Promise<void>((resolve) => pending.push(resolve));
          await gate;
        }
        const payload = barsFail ? { ok: false, status: 500 } : { bars: [barPayload()] };
        return respond(payload, !barsFail);
      }
      if (url.includes("/api/v1/channels")) {
        return respond({}, false);
      }
      if (url.includes("/api/v1/features/timeseries")) {
        return respond({ points: [] });
      }
      if (url.includes("/api/v1/extrema")) {
        return respond({ confirmed: [], candidates: [] });
      }
      if (url.includes("/api/v1/volume-profile")) {
        return respond({
          window: "24h",
          bins: [],
          poc_index: 0,
          value_area: [0, 0],
          covered_ns: 0,
          complete: true,
          width: 1,
        }, true);
      }
      if (url.includes("/api/v1/dex/depth")) {
        return respond({}, false);
      }
      return respond({}, false);
    }),
  );

  const advanceTimers = async (ms: number) => {
    await act(async () => {
      vi.advanceTimersByTime(ms);
    });
  };

  return {
    calls,
    advanceTimers,
    resolveBars: () => pending.shift()?.(),
    setBarsFail: (_fail: boolean) => { /* handled by barsFail in new harness */ },
  };
}

beforeEach(() => {
  openAt("");
  vi.useFakeTimers({ shouldAdvanceTime: true });
  // Set the refresh interval env for tests
  vi.stubGlobal("import.meta", { env: { VITE_CHART_REFRESH_MS: "60000" } });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("US1: timer fires on interval, calls load(), new bars drawn", () => {
  it("runs the timer and re-fetches bars on interval (default 60s)", async () => {
    const { calls, advanceTimers } = makeHarness();
    render(<App />);

    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined(), { timeout: 5000 });
    const initialBarsCalls = seriesCalls(calls, "/api/v1/bars").length;
    expect(initialBarsCalls).toBe(1);

    await advanceTimers(60_000);

    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars").length).toBe(2), { timeout: 5000 });
    expect(lastSeriesCall(calls, "/api/v1/bars")).toBeDefined();
  });

  it("pinned chart (at) issues zero timer requests", async () => {
    const { calls, advanceTimers } = makeHarness();
    openAt("?at=2026-01-01T00:00:00Z");
    render(<App />);

    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined(), { timeout: 5000 });
    const initialBarsCalls = seriesCalls(calls, "/api/v1/bars").length;

    await advanceTimers(60_000);
    await advanceTimers(60_000);
    await advanceTimers(60_000);

    expect(seriesCalls(calls, "/api/v1/bars").length).toBe(initialBarsCalls);
  });

  it("hidden tab issues zero requests while hidden, one on show", async () => {
    const { calls, advanceTimers } = makeHarness();
    render(<App />);

    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined(), { timeout: 5000 });
    const initialBarsCalls = seriesCalls(calls, "/api/v1/bars").length;

    // Hide the tab
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    await advanceTimers(60_000);
    await advanceTimers(60_000);

    expect(seriesCalls(calls, "/api/v1/bars").length).toBe(initialBarsCalls);

    // Show the tab
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars").length).toBe(initialBarsCalls + 1), { timeout: 5000 });
  });
});

describe("US1: overlapping ticks skipped (in-flight guard)", () => {
  it("second tick sees isLoading=true and skips", async () => {
    const calls: string[] = [];
    const pending: (() => void)[] = [];
    let barsCalls = 0;

    const respond = (payload: unknown, ok = true) => ({
      ok,
      status: ok ? 200 : 500,
      json: async () => payload,
    });

    vi.useFakeTimers({ shouldAdvanceTime: true });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(url);
        if (url.includes("/api/v1/timeframes")) {
          return respond(OFFERED, true);
        }
        if (isMinuteBuild(url)) {
          return respond({ bars: [] }, true);
        }
        if (url.includes("/api/v1/bars")) {
          barsCalls += 1;
          // The SECOND request is the first refresh; the first is the initial load, which must complete
          // (it is what produces the extrema call this test waits for before advancing the clock).
          if (barsCalls === 2) {
            const gate = new Promise<void>((resolve) => pending.push(resolve));
            await gate;
          }
          return respond({ bars: [barPayload()] }, true);
        }
        if (url.includes("/api/v1/channels")) {
          return respond({}, false);
        }
        if (url.includes("/api/v1/features/timeseries")) {
          return respond({ points: [] });
        }
        if (url.includes("/api/v1/extrema")) {
          return respond({ confirmed: [], candidates: [] });
        }
        if (url.includes("/api/v1/volume-profile")) {
          return respond({
            window: "24h",
            bins: [],
            poc_index: 0,
            value_area: [0, 0],
            covered_ns: 0,
            complete: true,
            width: 1,
          }, true);
        }
        return respond({}, false);
      }),
    );

    const advanceTimers = async (ms: number) => {
      await act(async () => {
        vi.advanceTimersByTime(ms);
      });
    };

    render(<App />);

    await waitFor(() => expect(calls.filter((u) => u.includes("/api/v1/extrema")).length).toBeGreaterThan(0), { timeout: 5000 });
    const initialBarsCalls = calls.filter((u) => u.includes("/api/v1/bars") && !isMinuteBuild(u)).length;

    // Advance past first interval (first refresh starts but defers)
    await advanceTimers(60_000);

    // Advance past second interval (second refresh should skip because first is in flight)
    await advanceTimers(60_000);

    // Resolve the first request
    pending[0]?.();

    await waitFor(() => expect(calls.filter((u) => u.includes("/api/v1/bars") && !isMinuteBuild(u)).length).toBe(initialBarsCalls + 1), { timeout: 5000 });
    // Should only have one additional bars call (the first refresh), not two
    expect(calls.filter((u) => u.includes("/api/v1/bars") && !isMinuteBuild(u)).length).toBe(initialBarsCalls + 1);
  });
});

describe("US3: refresh failure keeps picture, states failure, recovers on next success", () => {
  it("failed refresh shows 'Refresh failed: ...' in LoadState, keeps old bars", async () => {
    const calls: string[] = [];
    // The initial load must succeed: the failure is of a REFRESH, and a chart that never loaded has no
    // picture to keep. It is switched to failing below, after the first load has drawn.
    let barsShouldFail = false;

    const respond = (payload: unknown, ok = true) => ({
      ok,
      status: ok ? 200 : 500,
      json: async () => payload,
    });

    vi.useFakeTimers({ shouldAdvanceTime: true });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(url);
        if (url.includes("/api/v1/timeframes")) {
          return respond(OFFERED, true);
        }
        if (url.includes("/api/v1/bars")) {
          const payload = barsShouldFail ? { ok: false, status: 500 } : { bars: [barPayload()] };
          return respond(payload, !barsShouldFail);
        }
        if (url.includes("/api/v1/channels")) {
          return respond({}, false);
        }
        if (url.includes("/api/v1/features/timeseries")) {
          return respond({ points: [] });
        }
        if (url.includes("/api/v1/extrema")) {
          return respond({ confirmed: [], candidates: [] });
        }
        if (url.includes("/api/v1/volume-profile")) {
          return respond({
            window: "24h",
            bins: [],
            poc_index: 0,
            value_area: [0, 0],
            covered_ns: 0,
            complete: true,
            width: 1,
          }, true);
        }
        return respond({}, false);
      }),
    );

    const advanceTimers = async (ms: number) => {
      await act(async () => {
        vi.advanceTimersByTime(ms);
      });
    };

    render(<App />);

    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined(), { timeout: 5000 });

    // Make refresh fail
    barsShouldFail = true;

    await advanceTimers(60_000);

    await waitFor(() => expect(screen.getByText(/Refresh failed: HTTP 500/)).toBeVisible(), { timeout: 5000 });
    expect(screen.queryByText("No bars in this range.")).toBeNull();

    // Make refresh succeed
    barsShouldFail = false;

    await advanceTimers(60_000);

    await waitFor(() => expect(screen.queryByText(/Refresh failed/)).toBeNull(), { timeout: 5000 });
    expect(screen.getByTestId("chart")).toBeInTheDocument();
  });
});