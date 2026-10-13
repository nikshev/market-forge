// @trace: REQ-WP-102
// @trace: REQ-WP-106
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

/** The only timeframe the feed carries: the ingest's own bars. Longer windows are built from them (REQ-WP-106). */
export const LIVE_TIMEFRAME = "1m";

/** Its duration, which the page asks the table for when it builds a longer window out of minutes. */
export const LIVE_MINUTE_NS = 60_000_000_000;

/** How many live bars are kept: the API's cache is thirty minutes, so sixty is a margin and not a history. */
export const KEEP = 60;

export type LiveStatus = "connecting" | "live" | "delayed" | "off";

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

// --- the bar of a longer timeframe that is still being built (REQ-WP-106) ----------------------------------------------------------
//
// The table holds only closed windows of a longer timeframe -- a 4h bar appears hours after it opened, once the resampler has run -- so
// without this the chart's last candle is the previous window and the current price is not on it. The window in progress is made of the
// minutes: the stored ones and the live ones after them.

const MINUTE_NS = 60_000_000_000n;

/** The most windows built beyond the last stored one: a window closed but not yet stored, and the one in progress, with room to spare. */
export const MAX_FORMING = 8;

function floorDiv(a: bigint, b: bigint): bigint {
  const q = a / b;
  return a % b !== 0n && a < 0n !== b < 0n ? q - 1n : q;
}

/** The opening instant of the window `t` falls in, counting from `anchor`, any window's open: so a week that opens on a Monday stays on Mondays. */
export function bucketOpen(t: bigint, tfNs: bigint, anchor: bigint): bigint {
  return floorDiv(t - anchor, tfNs) * tfNs + anchor;
}

/** Stored minutes and live minutes as one series: oldest first, each minute once, the stored one superseding the live. */
export function mergeMinutes(stored: readonly BarOut[], live: readonly BarOut[]): BarOut[] {
  const byOpen = new Map<bigint, BarOut>();
  for (const bar of live) {
    byOpen.set(bar.open_time_ns, bar);
  }
  for (const bar of stored) {
    byOpen.set(bar.open_time_ns, bar);
  }
  return [...byOpen.values()].sort((a, b) => (a.open_time_ns < b.open_time_ns ? -1 : a.open_time_ns > b.open_time_ns ? 1 : 0));
}

/** One window out of the minutes in it: the first open, the highest high, the lowest low, the last close, the summed volume. Never final. */
export function aggregate(minutes: readonly BarOut[], openNs: bigint, tfNs: bigint): BarOut | null {
  if (minutes.length === 0) {
    return null;
  }
  const first = minutes[0]!;
  const last = minutes[minutes.length - 1]!;
  let high = first;
  let low = first;
  let volume = 0;
  for (const bar of minutes) {
    if (Number(bar.high) > Number(high.high)) {
      high = bar;
    }
    if (Number(bar.low) < Number(low.low)) {
      low = bar;
    }
    volume += Number(bar.volume_base);
  }
  return {
    open_time_ns: openNs,
    close_time_ns: openNs + tfNs,
    open: first.open,
    high: high.high,
    low: low.low,
    close: last.close,
    volume_base: String(volume),
    is_final: false,
  };
}

/**
 * The windows of `tfNs` after the last stored one, built from `minutes` (stored and live, already combined by `mergeMinutes`).
 *
 * The window in progress has the latest minute's price as its close. A window that has closed and is not stored yet is built too
 * -- the resampler runs every few minutes, and without it the chart would skip a candle until it had -- and is **final only if
 * every minute of it is there and itself final**: a window made of what happened to arrive is not claimed to be the bar.
 * Nothing is built from no minutes, so a feed that is down leaves the chart as it was.
 */
export function formingBars({
  stored,
  minutes,
  tfNs,
}: {
  stored: readonly BarOut[];
  minutes: readonly BarOut[];
  tfNs: bigint;
}): BarOut[] {
  if (minutes.length === 0) {
    return [];
  }
  const ordered = [...minutes].sort((a, b) => (a.open_time_ns < b.open_time_ns ? -1 : a.open_time_ns > b.open_time_ns ? 1 : 0));
  let lastStoredOpen: bigint | null = null;
  for (const bar of stored) {
    if (lastStoredOpen === null || bar.open_time_ns > lastStoredOpen) {
      lastStoredOpen = bar.open_time_ns;
    }
  }
  const anchor = lastStoredOpen ?? 0n;
  const latest = ordered[ordered.length - 1]!.open_time_ns;
  const lastWindow = bucketOpen(latest, tfNs, anchor);
  const firstWindow = lastStoredOpen === null ? bucketOpen(ordered[0]!.open_time_ns, tfNs, anchor) : lastStoredOpen + tfNs;
  const earliest = lastWindow - BigInt(MAX_FORMING - 1) * tfNs;
  const needed = Number(tfNs / MINUTE_NS);

  const built: BarOut[] = [];
  for (let open = firstWindow > earliest ? firstWindow : earliest; open <= lastWindow; open += tfNs) {
    const inside = ordered.filter((bar) => bar.open_time_ns >= open && bar.open_time_ns < open + tfNs);
    const bar = aggregate(inside, open, tfNs);
    if (bar === null) {
      continue;
    }
    const closed = open + tfNs <= latest + MINUTE_NS;
    built.push({ ...bar, is_final: closed && inside.length === needed && inside.every((m) => m.is_final) });
  }
  return built;
}
