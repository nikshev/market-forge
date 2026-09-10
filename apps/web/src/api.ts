// @trace: REQ-WP-009
//
// A typed client for PRD section 28. Every call reports a failure as a value
// rather than throwing into a render: FR-016 says a failed load must never be
// drawn as though it were data, and an exception escaping into React gets an
// empty component tree, which is exactly the indistinguishable blank the rule
// forbids.

import type {
  BarOut,
  ChannelMode,
  ChannelOut,
  ExtremaResponse,
  FeatureSeriesResponse,
  SignalOut,
} from "./types";
import { AS_SEEN_THEN } from "./types";

export type Result<T> = { ok: true; value: T } | { ok: false; error: string };

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string, params: Record<string, string | number>): Promise<Result<T>> {
  const query = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  ).toString();
  try {
    const response = await fetch(`${BASE}${path}?${query}`);
    if (!response.ok) {
      // The status is the detail a reader can act on. "Something went wrong"
      // sends them to the console.
      return { ok: false, error: `HTTP ${response.status}` };
    }
    return { ok: true, value: (await response.json()) as T };
  } catch (cause) {
    return { ok: false, error: cause instanceof Error ? cause.message : String(cause) };
  }
}

export function fetchBars(params: {
  venue: string;
  symbol: string;
  timeframeNs: number;
  limit?: number;
}): Promise<Result<{ bars: BarOut[] }>> {
  return get("/api/v1/bars", {
    venue: params.venue,
    symbol: params.symbol,
    timeframe_ns: params.timeframeNs,
    ...(params.limit === undefined ? {} : { limit: params.limit }),
  });
}

export function fetchChannel(params: {
  venue: string;
  symbol: string;
  timeframeNs: number;
  atNs: number;
  mode: ChannelMode;
}): Promise<Result<ChannelOut>> {
  return get("/api/v1/channels", {
    venue: params.venue,
    symbol: params.symbol,
    timeframe_ns: params.timeframeNs,
    at_ns: params.atNs,
    // The parameter is sent explicitly in both directions rather than omitted
    // for the default. An omitted parameter relies on the server's default
    // staying right; ADR-020 wants both ends stating the same thing.
    as_seen_then: params.mode === AS_SEEN_THEN ? "true" : "false",
  });
}

export function fetchSignal(signalId: string): Promise<Result<{ decision: SignalOut }>> {
  return get(`/api/v1/signals/${signalId}`, {});
}

export function fetchFeatureSeries(params: {
  venue: string;
  symbol: string;
  timeframeNs: number;
  startNs: number;
  endNs: number;
}): Promise<Result<FeatureSeriesResponse>> {
  return get("/api/v1/features/timeseries", {
    venue: params.venue,
    symbol: params.symbol,
    timeframe_ns: params.timeframeNs,
    start_ns: params.startNs,
    end_ns: params.endNs,
  });
}

export function fetchExtrema(params: {
  instrumentId: string;
  timeframeNs: number;
  asOfNs: number | null;
}): Promise<Result<ExtremaResponse>> {
  return get("/api/v1/extrema", {
    instrument_id: params.instrumentId,
    timeframe_ns: params.timeframeNs,
    // Omitted rather than sent as null when the caller has no instant: the
    // endpoint reads an absent `as_of_ns` as "everything on record", which is
    // what CURRENT REFIT wants.
    ...(params.asOfNs === null ? {} : { as_of_ns: params.asOfNs }),
  });
}
