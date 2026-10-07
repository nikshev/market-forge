// @trace: REQ-WP-091
//
// The page and the cross-venue consensus (T019): with `consensus` among the link's layers the page
// asks `/api/v1/consensus` for the market in the link, at the link's instant, for the timeframe in
// force -- and hands `Chart` the **array** of per-bar points, not the `ConsensusOut` envelope, whose
// shape `Chart`'s `consensus?: ConsensusPointOut[] | null` prop does not accept (T017's test pins the
// prop; this pins what the page puts in it). With the layer off it asks for nothing at all.

import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ConsensusOut } from "../types";

const api = vi.hoisted(() => ({ fetchConsensus: vi.fn() }));
const drawn = vi.hoisted(() => ({ consensus: [] as unknown[] }));

vi.mock("../api", () => ({
  fetchBars: async () => ({ ok: true, value: { bars: [] } }),
  fetchChannel: async () => ({ ok: false, error: "HTTP 404" }),
  fetchDexDepth: async () => ({ ok: false, error: "HTTP 404" }),
  fetchExtrema: async () => ({ ok: true, value: { confirmed: [], candidates: [] } }),
  fetchFeatureSeries: async () => ({ ok: true, value: { points: [] } }),
  fetchTimeframes: async () => ({
    ok: true,
    value: { timeframes: [{ token: "15m", timeframe_ns: 900_000_000_000 }] },
  }),
  fetchVolumeProfile: async () => ({ ok: false, error: "HTTP 404" }),
  fetchConsensus: api.fetchConsensus,
}));

vi.mock("../Chart", () => ({
  Chart: (props: { consensus?: unknown }) => {
    drawn.consensus.push(props.consensus);
    return <div data-testid="chart" />;
  },
}));

import { App } from "../App";

const envelope = (): ConsensusOut => ({
  consensus: [
    {
      bar_close_ns: 1_789_344_060_000_000_000n,
      consensus_mid: "2500.5",
      venue_count: 2,
      refusal_reason: null,
    },
  ],
  window: "24h",
  at_ns: 1_789_344_000_000_000_000n,
});

function open(search: string): void {
  window.history.pushState({}, "", `/chart/binance/BTCUSDT${search}`);
}

beforeEach(() => {
  api.fetchConsensus.mockReset();
  drawn.consensus.length = 0;
});

describe("the page and the cross-venue consensus", () => {
  it("asks for the consensus when the layer is on, and hands Chart the array of points", async () => {
    const value = envelope();
    api.fetchConsensus.mockResolvedValue({ ok: true, value });
    open("?tf=15m&overlays=candles,consensus");

    render(<App />);

    await waitFor(() => expect(api.fetchConsensus).toHaveBeenCalled());
    expect(api.fetchConsensus).toHaveBeenCalledWith({
      venue: "binance",
      symbol: "BTCUSDT",
      timeframeNs: 900_000_000_000,
      window: "24h",
      atNs: null,
    });

    // The array, not the envelope: `Chart`'s prop is `ConsensusPointOut[] | null`.
    await waitFor(() => expect(drawn.consensus.at(-1)).toEqual(value.consensus));
    expect(drawn.consensus.at(-1)).not.toEqual(value);
  });

  it("asks for nothing when the layer is off, and hands Chart no consensus", async () => {
    api.fetchConsensus.mockResolvedValue({ ok: true, value: envelope() });
    open("?tf=15m&overlays=candles");

    render(<App />);

    await waitFor(() => expect(screenReady()).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(api.fetchConsensus).not.toHaveBeenCalled();
    expect(drawn.consensus.at(-1) ?? null).toBeNull();
  });

  it("states a consensus the server has no answer for as absence, and draws nothing", async () => {
    api.fetchConsensus.mockResolvedValue({ ok: false, error: "HTTP 404" });
    open("?tf=15m&overlays=candles,consensus");

    render(<App />);

    await waitFor(() => expect(api.fetchConsensus).toHaveBeenCalled());
    await waitFor(() => expect(drawn.consensus.at(-1)).toBeNull());
  });
});

function screenReady(): boolean {
  return document.querySelector('[data-testid="chart"]') !== null;
}
