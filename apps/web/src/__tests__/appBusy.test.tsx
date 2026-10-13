// @trace: REQ-WP-103
//
// The chart page's waiting: a spinner over the chart until the first bars answer, a small one while a reload is in flight,
// one for the timeframes control, one for the consensus -- each gone when its own answer arrives, none when the answer is
// "nothing" or a failure.

import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../Chart", () => ({ Chart: () => <div data-testid="chart" /> }));
vi.mock("../useLiveBars", () => ({
  useLiveBars: () => ({ bars: [], status: "off" as const }),
}));

import { App } from "../App";

const MIN = 60_000_000_000;
const OFFERED = { timeframes: [{ token: "1m", timeframe_ns: MIN }, { token: "5m", timeframe_ns: 5 * MIN }] };
const BAR = {
  open_time_ns: "1789344000000000000",
  close_time_ns: "1789344060000000000",
  open: "100",
  high: "100",
  low: "100",
  close: "100",
  volume_base: "1",
  is_final: true,
};

type Gate = { promise: Promise<void>; open: () => void };
const gate = (): Gate => {
  let open: () => void = () => undefined;
  const promise = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { promise, open };
};

function harness(gates: { timeframes?: Gate; bars?: Gate; series?: Gate; consensus?: Gate; barsBody?: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const u = String(url);
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
      if (u.includes("/api/v1/timeframes")) {
        await gates.timeframes?.promise;
        return ok(OFFERED);
      }
      if (u.includes("/api/v1/bars")) {
        await gates.bars?.promise;
        return ok(gates.barsBody ?? { bars: [BAR] });
      }
      if (u.includes("/api/v1/features/timeseries")) {
        await gates.series?.promise;
        return ok({ points: [] });
      }
      if (u.includes("/api/v1/consensus")) {
        await gates.consensus?.promise;
        return ok({ consensus: [] });
      }
      if (u.includes("/api/v1/extrema")) {
        return ok({ confirmed: [], candidates: [] });
      }
      if (u.includes("/api/v1/volume-profile")) {
        return ok({ window: "24h", bins: [], poc_index: 0, value_area: [0, 0], covered_ns: 0, complete: true, width: 1 });
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }),
  );
}

function open(search = ""): void {
  window.history.replaceState(null, "", `/chart/bybit/BTCUSDT${search}`);
}

beforeEach(() => {
  open("?tf=1m");
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the chart page while it waits", () => {
  it("shows a spinner for the timeframes until they answer, then takes it away", async () => {
    const timeframes = gate();
    harness({ timeframes });
    render(<App />);

    expect(await screen.findByRole("progressbar", { name: "Loading timeframes" })).toBeInTheDocument();

    await act(async () => timeframes.open());
    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Loading timeframes" })).toBeNull());
  });

  it("covers the chart with a spinner until the first bars answer, then takes it away", async () => {
    const bars = gate();
    harness({ bars });
    render(<App />);

    expect(await screen.findByRole("progressbar", { name: "Loading the chart" })).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toBeInTheDocument(); // the chart is mounted under it, so it can draw the moment bars arrive

    await act(async () => bars.open());
    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Loading the chart" })).toBeNull());
  });

  it("takes the chart's spinner away when there are no bars: empty is an answer", async () => {
    harness({ barsBody: { bars: [] } });
    render(<App />);

    await waitFor(() => expect(screen.getByText(/No bars in this range/)).toBeInTheDocument());
    expect(screen.queryByRole("progressbar", { name: "Loading the chart" })).toBeNull();
  });

  it("takes it away when the bars fail, and says so", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        String(url).includes("/timeframes")
          ? { ok: true, status: 200, json: async () => OFFERED }
          : { ok: false, status: 500, json: async () => ({}) },
      ),
    );
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be loaded/i);
    expect(screen.queryByRole("progressbar", { name: "Loading the chart" })).toBeNull();
  });

  it("shows the pane's spinner while the series is outstanding, after the bars have answered", async () => {
    const series = gate();
    harness({ series });
    render(<App />);

    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Loading the chart" })).toBeNull());
    // Volume is made of the bars, which have answered; a pane made of the series is the one still waiting.
    expect(screen.queryByRole("progressbar", { name: "Loading the pane" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "OFI (1m)" }));
    expect(await screen.findByRole("progressbar", { name: "Loading the pane" })).toBeInTheDocument();

    await act(async () => series.open());
    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Loading the pane" })).toBeNull());
  });

  it("shows a spinner for the consensus while it is asked for, only when the layer is on", async () => {
    const consensus = gate();
    harness({ consensus });
    open("?tf=1m&overlays=candles,consensus");
    render(<App />);

    expect(await screen.findByRole("progressbar", { name: "Loading the consensus" })).toBeInTheDocument();

    await act(async () => consensus.open());
    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Loading the consensus" })).toBeNull());
  });

  it("asks for no consensus spinner when the layer is off", async () => {
    harness({});
    render(<App />);

    await waitFor(() => expect(screen.getByTestId("chart")).toBeInTheDocument());
    expect(screen.queryByRole("progressbar", { name: "Loading the consensus" })).toBeNull();
  });

  it("settles with no spinner left once everything has answered", async () => {
    harness({});
    render(<App />);

    await waitFor(() => expect(screen.queryAllByRole("progressbar")).toHaveLength(0), { timeout: 5000 });
  });
});
