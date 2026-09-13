// @trace: REQ-WP-009
//
// A typed client for PRD section 28. Every call reports a failure as a value
// rather than throwing into a render: FR-016 says a failed load must never be
// drawn as though it were data, and an exception escaping into React gets an
// empty component tree, which is exactly the indistinguishable blank the rule
// forbids.

import type {
  BarOut,
  DexDepthResponse,
  ChannelMode,
  ChannelOut,
  ExtremaResponse,
  FeatureSeriesResponse,
  SignalOut,
} from "./types";
import { BadTime, nanoseconds } from "./time";
import { AS_SEEN_THEN } from "./types";

export type Result<T> = { ok: true; value: T } | { ok: false; error: string };

// Every `_ns` key the API sends is converted here, once, by one rule: a **string**
// is an instant and becomes a `bigint`; a **number** is a duration and stays one.
//
// That rule is safe because the other end enforces it. `tests/unit/api/
// test_wire_time.py` asserts field by field which `_ns` fields of which schema
// are strings and which are integers, and fails when a new one is added without
// choosing -- so a timestamp cannot arrive here as a number and be quietly
// accepted as a span.
//
// Conversion happens inside this module because a bad value has to become a
// `Result` failure. REQ-WP-009's FR-016 says a failed load is stated and never
// rendered, and `BigInt("abc")` thrown in a component gets an empty tree --
// exactly the indistinguishable blank the rule forbids.
function convertTimes(value: unknown, path = ""): unknown {
  if (Array.isArray(value)) {
    return value.map((item, index) => convertTimes(item, `${path}[${index}]`));
  }
  if (value === null || typeof value !== "object") {
    return value;
  }
  const converted: Record<string, unknown> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    const where = path === "" ? key : `${path}.${key}`;
    if (!key.endsWith("_ns")) {
      converted[key] = convertTimes(raw, where);
      continue;
    }
    // A null instant is a real answer -- `state_time_ns` is null for a pool with
    // no curve -- and is left alone. A number is a duration. Anything else is an
    // instant and is validated.
    converted[key] = raw === null || typeof raw === "number" ? raw : nanoseconds(raw, where);
  }
  return converted;
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(
  path: string,
  // `bigint` is accepted and stringified exactly. Sending an instant as a number
  // would round it on the way *out*, which for `as_of_ns` means asking the
  // server about a slightly different moment than the chart is showing.
  params: Record<string, string | number | bigint>,
): Promise<Result<T>> {
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
    return { ok: true, value: convertTimes(await response.json()) as T };
  } catch (cause) {
    if (cause instanceof BadTime) {
      // Named, because this failure is about the payload rather than the
      // network, and a reader who sees it should suspect the server.
      return { ok: false, error: `the response carried an unreadable time — ${cause.message}` };
    }
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
  atNs: bigint;
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
  startNs: bigint;
  endNs: bigint;
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
  asOfNs: bigint | null;
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

export function fetchDexDepth(params: {
  chainId: number;
  pool: string;
  atNs: bigint;
}): Promise<Result<DexDepthResponse>> {
  // `atNs` is not optional here either. The endpoint requires it, and a client
  // that filled it in would put the decision somewhere the reader of a chart
  // cannot see.
  return get("/api/v1/dex/depth", {
    chain_id: params.chainId,
    pool: params.pool,
    at_ns: params.atNs,
  });
}
