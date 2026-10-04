// @trace: REQ-WP-085
//
// The page with its API replaced. Volume comes from the bars, so it does not wait for the feature series,
// is not taken away by a failed one, and says "no data" the moment the bars are known to be none -- even though
// the page then never requests the feature series at all.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  bars: null as null | (() => Promise<unknown>),
  series: null as null | (() => Promise<unknown>),
  seriesCalls: 0,
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
  fetchBars: () => api.bars?.(),
  fetchChannel: async () => ({ ok: false, error: "no channel" }),
  fetchExtrema: async () => ({ ok: true, value: { confirmed: [], candidates: [] } }),
  fetchDexDepth: async () => ({ ok: false, error: "none" }),
  fetchFeatureSeries: () => {
    api.seriesCalls += 1;
    return api.series?.();
  },
}));

import { App } from "../App";

const bar = (i: number, isFinal = true) => ({
  open_time_ns: 1788838800000000000n + BigInt(i) * 900_000_000_000n,
  close_time_ns: 1788838800000000000n + BigInt(i + 1) * 900_000_000_000n,
  open: "100",
  high: "101",
  low: "99",
  close: "100",
  volume_base: String(i + 1),
  is_final: isFinal,
});
const withBars = (n: number) => async () => ({
  ok: true,
  value: { bars: Array.from({ length: n }, (_, i) => bar(i)) },
});
const features = (values: Record<string, number>[]) => async () => ({
  ok: true,
  value: {
    points: values.map((v, i) => ({ at_ns: 1788838800000000000n + BigInt(i) * 1_000_000_000n, values: v })),
  },
});

describe("Volume on the chart page", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/chart/binance/BTCUSDT?tf=15m");
    api.seriesCalls = 0;
  });

  it("is the pane the page opens on when there are bars and the features have nothing", async () => {
    api.bars = withBars(3);
    api.series = features([]);

    render(<App />);

    expect(await screen.findByRole("img", { name: /volume over 3 point/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Volume" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(9));
    expect(screen.queryByRole("status", { name: "Pane contents" })).toBeNull();
  });

  it("stays live and drawn when the feature load fails, and no pane says 'no data'", async () => {
    api.bars = withBars(3);
    api.series = async () => ({ ok: false, error: "HTTP 503" });

    render(<App />);

    expect(await screen.findByRole("img", { name: /volume over 3 point/ })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Pane load" })).toBeNull();
    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();
  });

  it("says 'no data' at once when the bars are none, and never asks for the features", async () => {
    api.bars = withBars(0);
    api.series = features([{ cvd: 1 }]);

    render(<App />);

    expect(await screen.findByRole("button", { name: "Volume no data" })).toBeDisabled();
    expect(api.seriesCalls).toBe(0);
  });

  it("says no pane has data only when Volume has none either: the only bar is still forming", async () => {
    api.bars = async () => ({ ok: true, value: { bars: [bar(0, false)] } });
    api.series = features([]);

    render(<App />);

    // Volume, selected from the start, first says its own bars are none; once the features have answered too,
    // the page knows no pane has data and says that.
    await waitFor(() =>
      expect(screen.getByRole("status", { name: "Pane contents" })).toHaveTextContent(
        "No pane has data for this view",
      ),
    );
    expect(screen.getAllByRole("button", { name: /no data$/ })).toHaveLength(10);
  });

  it("does not say 'no finished bars' of Volume before the bars have answered", async () => {
    let release: (value: unknown) => void = () => {};
    api.bars = () => new Promise((resolve) => (release = resolve));
    api.series = features([]);

    render(<App />);

    expect(await screen.findByRole("group", { name: "Pane" })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Pane contents" })).toBeNull();
    release({ ok: true, value: { bars: [bar(0)] } });
    await screen.findByRole("img", { name: /volume over 1 point/ });
  });

  it("claims nothing of Volume before the bars have answered", async () => {
    let release: (value: unknown) => void = () => {};
    api.bars = () => new Promise((resolve) => (release = resolve));
    api.series = features([]);

    render(<App />);

    expect(await screen.findByRole("group", { name: "Pane" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /no data/ })).toBeNull();

    release({ ok: true, value: { bars: [bar(0)] } });
    await screen.findByRole("img", { name: /volume over 1 point/ });
  });

  it("does not take a reader's choice of a feature pane away when the data is fetched again", async () => {
    api.bars = withBars(3);
    api.series = features([{ ofi_1m: 1 }]);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "OFI (1m)" }));
    fireEvent.click(await screen.findByRole("button", { name: "5m" }));
    fireEvent.click(await screen.findByRole("button", { name: "15m" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "OFI (1m)" })).toHaveAttribute("aria-pressed", "true"),
    );
  });
});
