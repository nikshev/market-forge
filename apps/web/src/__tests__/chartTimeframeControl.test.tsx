// @trace: REQ-WP-074
//
// The whole mechanism at the page level: the link's timeframe reaches all four
// requests, the control changes them, the last choice wins, and the empty/failed
// vocabulary does not drift while the request path is rewritten.
//
// The assertions are on the URLs that reached `fetch`, not on component state:
// a constant `15 * MINUTE_NS` passes any test that inspects what React holds,
// and the defect being removed is exactly that constant.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

// The chart library needs a layout engine and canvas, neither of which jsdom
// has. These tests are about what the page requests and what it says, not about
// candles -- `Chart.test.tsx` covers the series decision without a renderer.
vi.mock("../Chart", () => ({
  Chart: () => <div data-testid="chart" />,
}));

const MINUTE_NS = 60_000_000_000;

const OFFERED = {
  timeframes: [
    { token: "1m", timeframe_ns: 60_000_000_000 },
    { token: "5m", timeframe_ns: 300_000_000_000 },
    { token: "15m", timeframe_ns: 900_000_000_000 },
    { token: "30m", timeframe_ns: 1_800_000_000_000 },
    { token: "1h", timeframe_ns: 3_600_000_000_000 },
    { token: "4h", timeframe_ns: 14_400_000_000_000 },
  ],
};

function barPayload(openNs = 1_789_344_000_000_000_000n, close = "100") {
  return {
    open_time_ns: String(openNs),
    close_time_ns: String(openNs + BigInt(MINUTE_NS)),
    open: close,
    high: close,
    low: close,
    close,
    volume_base: "1",
    is_final: true,
  };
}

interface Harness {
  calls: string[];
  resolveBars: (index: number) => void;
}

interface HarnessOptions {
  bars?: unknown;
  barsOk?: boolean;
  deferBars?: number;
  offered?: unknown;
  offeredOk?: boolean;
}

/** A fetch that answers every endpoint the page uses, recording the URLs. */
function harness(options: HarnessOptions = {}): Harness {
  const calls: string[] = [];
  const pending: (() => void)[] = [];
  let barsCalls = 0;
  const deferredFor = options.deferBars ?? 0;

  const respond = (payload: unknown, ok = true) => ({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload,
  });

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      if (url.includes("/api/v1/timeframes")) {
        return respond(options.offered ?? OFFERED, options.offeredOk ?? true);
      }
      if (url.includes("/api/v1/bars")) {
        barsCalls += 1;
        if (barsCalls <= deferredFor) {
          const gate = new Promise<void>((resolve) => pending.push(resolve));
          await gate;
        }
        const payload = options.bars ?? { bars: [barPayload()] };
        return respond(payload, options.barsOk ?? true);
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
      return respond({}, false);
    }),
  );

  return { calls, resolveBars: (index) => pending[index]?.() };
}

function openAt(search: string): void {
  window.history.replaceState(null, "", `/chart/binance/BTCUSDT${search}`);
}

function seriesCalls(calls: string[], path: string): string[] {
  return calls.filter((url) => url.includes(path));
}

function lastSeriesCall(calls: string[], path: string): string | undefined {
  return seriesCalls(calls, path).at(-1);
}

beforeEach(() => {
  openAt("");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("US1: the in-force timeframe reaches every request", () => {
  it("carries the link's tf on all four series", async () => {
    openAt("?tf=4h");
    const { calls } = harness();

    render(<App />);

    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined());
    for (const path of [
      "/api/v1/bars",
      "/api/v1/channels",
      "/api/v1/features/timeseries",
      "/api/v1/extrema",
    ]) {
      expect(lastSeriesCall(calls, path)).toContain("timeframe_ns=14400000000000");
      expect(seriesCalls(calls, path)).toHaveLength(1);
    }
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("4h");
  });

  it("re-reads all four at the chosen timeframe", async () => {
    openAt("?tf=4h");
    const { calls } = harness();
    render(<App />);
    await waitFor(() => expect(lastSeriesCall(calls, "/api/v1/extrema")).toBeDefined());

    await userEvent.click(screen.getByRole("button", { name: "5m" }));

    await waitFor(() =>
      expect(lastSeriesCall(calls, "/api/v1/extrema")).toContain("timeframe_ns=300000000000"),
    );
    for (const path of [
      "/api/v1/bars",
      "/api/v1/channels",
      "/api/v1/features/timeseries",
      "/api/v1/extrema",
    ]) {
      expect(lastSeriesCall(calls, path)).toContain("timeframe_ns=300000000000");
    }
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("5m");
  });

  it("issues no series request before the offered set has arrived", async () => {
    openAt("?tf=1h");
    const calls: string[] = [];
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(url);
        if (url.includes("/api/v1/timeframes")) {
          await gate;
          return { ok: true, status: 200, json: async () => OFFERED };
        }
        return { ok: true, status: 200, json: async () => ({ bars: [barPayload()] }) };
      }),
    );

    render(<App />);
    await Promise.resolve();
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);

    release?.();
    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(1));
    expect(seriesCalls(calls, "/api/v1/bars")[0]).toContain("timeframe_ns=3600000000000");
  });

  it("keeps the last choice when responses arrive out of order", async () => {
    openAt("?tf=15m");
    const { calls, resolveBars } = harness({ deferBars: 1 });
    render(<App />);
    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(1));

    await userEvent.click(screen.getByRole("button", { name: "5m" }));
    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(2));

    resolveBars(0);
    await waitFor(() =>
      expect(lastSeriesCall(calls, "/api/v1/extrema")).toContain("timeframe_ns=300000000000"),
    );
    // The initial bars request at 15m is legitimate -- it was issued before the
    // click. What must not happen is the superseded load running on to its
    // channel, features and extrema requests at the old timeframe.
    expect(seriesCalls(calls, "/api/v1/bars")).toEqual([
      expect.stringContaining("timeframe_ns=900000000000"),
      expect.stringContaining("timeframe_ns=300000000000"),
    ]);
    for (const path of [
      "/api/v1/channels",
      "/api/v1/features/timeseries",
      "/api/v1/extrema",
    ]) {
      expect(seriesCalls(calls, path).some((url) => url.includes("timeframe_ns=900000000000"))).toBe(
        false,
      );
    }
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("5m");
  });
});

describe("US1 regression: empty and failed stay distinct", () => {
  it("reads an empty series as empty, not as a failure", async () => {
    openAt("?tf=15m");
    harness({ bars: { bars: [] } });

    render(<App />);

    await waitFor(() => expect(screen.getByText("No bars in this range.")).toBeVisible());
    expect(screen.queryByText(/could not be loaded/)).toBeNull();
  });

  it("reads a failed request as failed, never as an empty market", async () => {
    openAt("?tf=15m");
    harness({ barsOk: false });

    render(<App />);

    await waitFor(() => expect(screen.getByText(/could not be loaded: HTTP 500/)).toBeVisible());
    expect(screen.queryByText("No bars in this range.")).toBeNull();
  });
});

describe("US2: the link opens at its own timeframe, or says why it cannot", () => {
  it("uses the documented default when the link names no timeframe", async () => {
    openAt("");
    const { calls } = harness();

    render(<App />);

    await waitFor(() => expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(1));
    expect(seriesCalls(calls, "/api/v1/bars")[0]).toContain("timeframe_ns=900000000000");
  });

  it("refuses an unparseable token visibly, naming it, with no requests", async () => {
    openAt("?tf=7m");
    const { calls } = harness();

    render(<App />);

    await waitFor(() => expect(screen.getByText(/Cannot show 7m/)).toBeVisible());
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);
    expect(screen.queryByTestId("chart")).toBeNull();
  });

  it("refuses a calendar period the same way", async () => {
    openAt("?tf=1M");
    const { calls } = harness();

    render(<App />);

    await waitFor(() => expect(screen.getByText(/Cannot show 1M/)).toBeVisible());
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);
  });

  it("refuses a valid token the deployment does not produce, listing what it does", async () => {
    openAt("?tf=1w");
    const { calls } = harness();

    render(<App />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Cannot show 1w");
    expect(alert).toHaveTextContent("1m, 5m, 15m, 30m, 1h, 4h");
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);
    expect(screen.queryByTestId("chart")).toBeNull();
  });

  it("refuses a default the deployment does not offer, rather than choosing a neighbour", async () => {
    openAt("");
    const { calls } = harness({
      offered: {
        timeframes: [
          { token: "1m", timeframe_ns: 60_000_000_000 },
          { token: "1h", timeframe_ns: 3_600_000_000_000 },
        ],
      },
    });

    render(<App />);

    await waitFor(() => expect(screen.getByText(/Cannot show 15m/)).toBeVisible());
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);
    expect(screen.queryByTestId("chart")).toBeNull();
  });

  it("states an offered-set failure instead of drawing an empty control", async () => {
    openAt("?tf=1h");
    const { calls } = harness({ offeredOk: false });

    render(<App />);

    await waitFor(() => expect(screen.getByText(/could not be loaded: HTTP 500/)).toBeVisible());
    expect(screen.queryByRole("button", { name: "1h" })).toBeNull();
    expect(screen.queryByTestId("chart")).toBeNull();
    expect(seriesCalls(calls, "/api/v1/bars")).toHaveLength(0);
  });
});

describe("US3: the address keeps up with the controls", () => {
  it("writes the chosen timeframe into the address", async () => {
    openAt("?tf=1h");
    harness();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "30m" })).toBeVisible());

    await userEvent.click(screen.getByRole("button", { name: "30m" }));

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get("tf")).toBe("30m");
    });
  });

  it("keeps the rest of the link when the timeframe changes", async () => {
    openAt("?tf=1h&at=2026-09-14T00%3A00%3A00Z&signal=6f3d1a2e");
    harness();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "4h" })).toBeVisible());

    await userEvent.click(screen.getByRole("button", { name: "4h" }));

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get("tf")).toBe("4h");
      expect(params.get("at")).toBe("2026-09-14T00:00:00Z");
      expect(params.get("signal")).toBe("6f3d1a2e");
    });
  });

  it("describes the mode in the address, both ways", async () => {
    openAt("?tf=1h");
    harness();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: /show current refit/i })).toBeVisible());

    await userEvent.click(screen.getByRole("button", { name: /show current refit/i }));
    await waitFor(() =>
      expect(new URLSearchParams(window.location.search).get("as_seen_then")).toBe("false"),
    );

    await userEvent.click(screen.getByRole("button", { name: /show as-seen-then/i }));
    await waitFor(() =>
      expect(new URLSearchParams(window.location.search).get("as_seen_then")).toBeNull(),
    );
  });

  it("opens a copied link at the same request the screen last made", async () => {
    openAt("?tf=1h");
    const screenRun = harness();
    const view = render(<App />);
    await waitFor(() => expect(seriesCalls(screenRun.calls, "/api/v1/bars")).toHaveLength(1));

    await userEvent.click(screen.getByRole("button", { name: "30m" }));
    await waitFor(() =>
      expect(lastSeriesCall(screenRun.calls, "/api/v1/bars")).toContain("timeframe_ns=1800000000000"),
    );
    const copiedSearch = window.location.search;
    const lastRequest = lastSeriesCall(screenRun.calls, "/api/v1/bars");

    view.unmount();
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", `/chart/binance/BTCUSDT${copiedSearch}`);

    const reopened = harness();
    render(<App />);
    await waitFor(() => expect(seriesCalls(reopened.calls, "/api/v1/bars")).toHaveLength(1));
    expect(seriesCalls(reopened.calls, "/api/v1/bars")[0]).toBe(lastRequest);
  });
});

describe("US4: the control offers what the deployment reported", () => {
  it("renders an unseen set and requests one of its tokens", async () => {
    // Tokens no source file names and no previous fixture used. If the frontend
    // carried a list, they could not render at all.
    openAt("?tf=2h");
    const { calls } = harness({
      offered: {
        timeframes: [
          { token: "1m", timeframe_ns: 60_000_000_000 },
          { token: "2h", timeframe_ns: 7_200_000_000_000 },
          { token: "12h", timeframe_ns: 43_200_000_000_000 },
        ],
      },
    });

    render(<App />);

    const control = await screen.findByRole("region", { name: "Timeframe" });
    expect(within(control).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "1m",
      "2h",
      "12h",
    ]);
    await waitFor(() =>
      expect(lastSeriesCall(calls, "/api/v1/bars")).toContain("timeframe_ns=7200000000000"),
    );

    await userEvent.click(screen.getByRole("button", { name: "12h" }));
    await waitFor(() =>
      expect(lastSeriesCall(calls, "/api/v1/bars")).toContain("timeframe_ns=43200000000000"),
    );
  });

  it("keeps no timeframe token list in the frontend sources", () => {
    // An absence, which no runtime assertion can see -- the same argument
    // REQ-WP-073's T034 makes for the producer. The default is the one allowed
    // literal, and it lives in timeframes.ts.
    const sources = import.meta.glob("../**/*.{ts,tsx}", {
      query: "?raw",
      import: "default",
      eager: true,
    }) as Record<string, string>;

    const offenders = Object.entries(sources)
      .filter(([path]) => !/\.test\.tsx?$/.test(path) && !path.endsWith("timeframes.ts"))
      .filter(([, source]) => /["'](1m|5m|30m|1h|4h|1d|1w)["']/.test(source))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});
