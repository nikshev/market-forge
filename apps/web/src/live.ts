// @trace: REQ-WP-102
//
// The chart's real-time feed, the pure half (REQ-WP-102): what a message from the socket is, how the live bars combine
// with the stored ones, and the socket's address and back-off. The socket itself is `useLiveBars`.
//
// Three rules carry the whole thing. **A stored bar supersedes a live one** for its minute, always: the table is the record and
// the live feed is a view that runs ahead of it. **A final bar is never replaced** -- not by a forming one, however late,
// and not by a second final one: a published bar is not amended, and a chart that showed an amendment would be repainting.
// And **one unreadable frame is not the end of the feed**: it is dropped and the next one is read.

import { BadTime, nanoseconds } from "./time";
import type { BarOut } from "./types";

/** Where the page connects: under `/api/v1/`, so the public proxy's one location reaches it and the gate verifies it. */
export const LIVE_PATH = "/api/v1/live";

/** The only timeframe the feed carries. */
export const LIVE_TIMEFRAME = "1m";

/** How many live bars are kept: the API's cache is thirty minutes, so sixty is a margin and not a history. */
export const KEEP = 60;

export type LiveStatus = "live" | "delayed" | "off";

/** A bar as the socket sends it: the REST bar, with the series it belongs to. */
export interface WireBar {
  venue: string;
  symbol: string;
  open_time_ns: string;
  close_time_ns: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume_base: string;
  is_final: boolean;
}

export type LiveMessage =
  | { kind: "ack"; live: boolean }
  | { kind: "error"; error: string }
  | { kind: "snapshot"; bars: BarOut[] }
  | { kind: "bar"; bar: BarOut };

export function fromWire(wire: WireBar): BarOut {
  return {
    open_time_ns: nanoseconds(wire.open_time_ns, "open_time_ns"),
    close_time_ns: nanoseconds(wire.close_time_ns, "close_time_ns"),
    open: wire.open,
    high: wire.high,
    low: wire.low,
    close: wire.close,
    volume_base: wire.volume_base,
    is_final: wire.is_final,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** One frame of text, or `null` if it is not one this page acts on. Never throws. */
export function parseMessage(text: string): LiveMessage | null {
  let message: unknown;
  try {
    message = JSON.parse(text);
  } catch {
    return null;
  }
  if (!isRecord(message)) {
    return null;
  }
  if (message["ok"] === true) {
    return { kind: "ack", live: message["live"] === true };
  }
  if (message["ok"] === false) {
    return { kind: "error", error: String(message["error"] ?? "refused") };
  }
  if (message["channel"] !== "bars" || !isRecord(message["data"])) {
    return null;
  }
  const data = message["data"];
  try {
    if (Array.isArray(data["snapshot"])) {
      return { kind: "snapshot", bars: (data["snapshot"] as WireBar[]).map(fromWire) };
    }
    if (isRecord(data["bar"])) {
      return { kind: "bar", bar: fromWire(data["bar"] as unknown as WireBar) };
    }
  } catch (error) {
    if (error instanceof BadTime) {
      return null;
    }
    throw error;
  }
  return null;
}

/** The held bars with `incoming` applied: oldest first, one per minute, a final bar never replaced. */
export function applyBar(held: readonly BarOut[], incoming: BarOut): BarOut[] {
  const next = new Map<bigint, BarOut>(held.map((b) => [b.open_time_ns, b]));
  const current = next.get(incoming.open_time_ns);
  if (current === undefined || !current.is_final) {
    next.set(incoming.open_time_ns, incoming);
  }
  return [...next.values()]
    .sort((a, b) => (a.open_time_ns < b.open_time_ns ? -1 : a.open_time_ns > b.open_time_ns ? 1 : 0))
    .slice(-KEEP);
}

/** The live bars that come after every stored one: what the chart draws beyond what the table has. */
export function liveAfter(stored: readonly BarOut[], live: readonly BarOut[]): BarOut[] {
  let last: bigint | null = null;
  for (const bar of stored) {
    if (last === null || bar.open_time_ns > last) {
      last = bar.open_time_ns;
    }
  }
  return live.filter((bar) => last === null || bar.open_time_ns > last);
}

/** `wss` on https and `ws` on http, on the page's own host unless an API base is configured. */
export function socketUrl(location: { protocol: string; host: string }, apiBase = ""): string {
  if (apiBase !== "") {
    const url = new URL(apiBase);
    return `${url.protocol === "https:" ? "wss:" : "ws:"}//${url.host}${LIVE_PATH}`;
  }
  return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}${LIVE_PATH}`;
}

/** The launch data as the socket's subprotocols: a browser cannot set a header on a WebSocket and a URL is logged. */
export function protocolsFor(launch: string): string[] {
  if (launch === "") {
    return [];
  }
  const bytes = new TextEncoder().encode(launch);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  const token = btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return ["tma", token];
}

/** A second, doubling to half a minute: a broker or a proxy that is down is asked again, not hammered. */
export function reconnectDelayMs(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 30_000);
}
