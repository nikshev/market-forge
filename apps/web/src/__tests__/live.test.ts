// @trace: REQ-WP-102
//
// The live feed's pure half: what a message is, how live bars combine with the stored ones, and the socket's address
// and back-off. Instants are `bigint` (REQ-WP-061), and a stored bar always supersedes a live one for its minute.

import { describe, expect, it } from "vitest";

import {
  LIVE_PATH,
  applyBar,
  fromWire,
  liveAfter,
  parseMessage,
  protocolsFor,
  reconnectDelayMs,
  socketUrl,
  type WireBar,
} from "../live";
import type { BarOut } from "../types";

const MIN = 60_000_000_000n;
const T0 = 1_788_800_000_000_000_000n - ((1_788_800_000_000_000_000n) % MIN);

const wire = (minute: number, over: Partial<WireBar> = {}): WireBar => ({
  venue: "bybit",
  symbol: "BTCUSDT",
  open_time_ns: String(T0 + BigInt(minute) * MIN),
  close_time_ns: String(T0 + BigInt(minute + 1) * MIN),
  open: "100",
  high: "102",
  low: "99",
  close: "101",
  volume_base: "3",
  is_final: false,
  ...over,
});
const bar = (minute: number, over: Partial<WireBar> = {}): BarOut => fromWire(wire(minute, over));

describe("fromWire", () => {
  it("reads the nanosecond instants exactly, as bigint", () => {
    const b = fromWire(wire(2, { open_time_ns: "1788800000123456789", close_time_ns: "1788800060123456789" }));

    expect(b.open_time_ns).toBe(1788800000123456789n);
    expect(b.close_time_ns).toBe(1788800060123456789n);
  });

  it("keeps the prices and volume as the strings the API sends and drops the series identity", () => {
    const b = fromWire(wire(0, { close: "101.50", volume_base: "3.25", is_final: true }));

    expect(b).toEqual({
      open_time_ns: T0,
      close_time_ns: T0 + MIN,
      open: "100",
      high: "102",
      low: "99",
      close: "101.50",
      volume_base: "3.25",
      is_final: true,
    });
  });

  it("refuses an instant that is not a nanosecond count rather than placing a bar at the epoch", () => {
    expect(() => fromWire(wire(0, { open_time_ns: "" }))).toThrow();
    expect(() => fromWire(wire(0, { close_time_ns: "12.5" }))).toThrow();
  });
});

describe("parseMessage", () => {
  const frame = (o: unknown): string => JSON.stringify(o);

  it("reads an acknowledgement and whether the feed is live for it", () => {
    expect(parseMessage(frame({ ok: true, live: true }))).toEqual({ kind: "ack", live: true });
    expect(parseMessage(frame({ ok: true, live: false }))).toEqual({ kind: "ack", live: false });
  });

  it("reads a refusal as an error carrying the reason", () => {
    expect(parseMessage(frame({ ok: false, error: "bad" }))).toEqual({ kind: "error", error: "bad" });
  });

  it("reads a snapshot as the bars of the cache, in the order sent", () => {
    const m = parseMessage(frame({ channel: "bars", data: { snapshot: [wire(0), wire(1)] } }));

    expect(m).toEqual({ kind: "snapshot", bars: [bar(0), bar(1)] });
  });

  it("reads an update as one bar", () => {
    expect(parseMessage(frame({ channel: "bars", data: { bar: wire(3) } }))).toEqual({ kind: "bar", bar: bar(3) });
  });

  it.each(["not json", "[]", "null", frame({ channel: "signals", data: {} }), frame({ channel: "bars", data: {} })])(
    "answers null, and does not throw, for %s",
    (text) => {
      expect(parseMessage(text)).toBeNull();
    },
  );

  it("answers null for a bar it cannot read rather than letting one bad frame end the feed", () => {
    expect(parseMessage(frame({ channel: "bars", data: { bar: wire(0, { open_time_ns: "x" }) } }))).toBeNull();
  });
});

describe("applyBar", () => {
  it("adds a bar and keeps them oldest first", () => {
    const got = applyBar(applyBar([], bar(2)), bar(1));

    expect(got.map((b) => b.open_time_ns)).toEqual([T0 + MIN, T0 + 2n * MIN]);
  });

  it("replaces the bar of the same minute by a later forming one", () => {
    const got = applyBar([bar(0, { close: "101" })], bar(0, { close: "105" }));

    expect(got).toHaveLength(1);
    expect(got[0]!.close).toBe("105");
  });

  it("replaces a forming bar by the final one", () => {
    const got = applyBar([bar(0, { close: "101" })], bar(0, { close: "102", is_final: true }));

    expect(got[0]).toMatchObject({ close: "102", is_final: true });
  });

  it("never replaces a final bar by a forming one", () => {
    const got = applyBar([bar(0, { close: "102", is_final: true })], bar(0, { close: "999" }));

    expect(got[0]).toMatchObject({ close: "102", is_final: true });
  });

  it("does not amend a final bar with a second final one", () => {
    const got = applyBar([bar(0, { close: "102", is_final: true })], bar(0, { close: "777", is_final: true }));

    expect(got[0]!.close).toBe("102");
  });

  it("does not change its input", () => {
    const before = [bar(0)];
    applyBar(before, bar(1));

    expect(before).toHaveLength(1);
  });

  it("keeps the newest sixty minutes and no more", () => {
    let held: BarOut[] = [];
    for (let m = 0; m < 80; m += 1) {
      held = applyBar(held, bar(m, { is_final: true }));
    }

    expect(held).toHaveLength(60);
    expect(held[0]!.open_time_ns).toBe(T0 + 20n * MIN);
    expect(held.at(-1)!.open_time_ns).toBe(T0 + 79n * MIN);
  });
});

describe("liveAfter", () => {
  it("keeps only the live bars after the last stored bar", () => {
    const stored = [bar(0, { is_final: true }), bar(1, { is_final: true })];
    const live = [bar(0), bar(1), bar(2), bar(3)];

    expect(liveAfter(stored, live).map((b) => b.open_time_ns)).toEqual([T0 + 2n * MIN, T0 + 3n * MIN]);
  });

  it("lets a stored bar supersede the live one for its minute, final or not", () => {
    const stored = [bar(5, { close: "STORED", is_final: true })];

    expect(liveAfter(stored, [bar(5, { close: "LIVE", is_final: true })])).toEqual([]);
  });

  it("keeps every live bar when nothing is stored yet", () => {
    expect(liveAfter([], [bar(0), bar(1)])).toHaveLength(2);
  });

  it("keeps the live order whatever the stored order", () => {
    const stored = [bar(3, { is_final: true }), bar(1, { is_final: true })];

    expect(liveAfter(stored, [bar(4), bar(5)]).map((b) => b.open_time_ns)).toEqual([T0 + 4n * MIN, T0 + 5n * MIN]);
  });
});

describe("the socket's address", () => {
  it("is wss on https and ws on http, on the page's own host, at the gated path", () => {
    expect(LIVE_PATH).toBe("/api/v1/live");
    expect(socketUrl({ protocol: "https:", host: "app.example" })).toBe("wss://app.example/api/v1/live");
    expect(socketUrl({ protocol: "http:", host: "127.0.0.1:8081" })).toBe("ws://127.0.0.1:8081/api/v1/live");
  });

  it("follows an explicit API base when one is configured", () => {
    expect(socketUrl({ protocol: "http:", host: "x" }, "https://api.example")).toBe("wss://api.example/api/v1/live");
    expect(socketUrl({ protocol: "https:", host: "x" }, "http://localhost:8000")).toBe("ws://localhost:8000/api/v1/live");
  });
});

describe("protocolsFor", () => {
  it("offers none without launch data, so outside Telegram the socket is plain", () => {
    expect(protocolsFor("")).toEqual([]);
  });

  it("offers the scheme and the launch data base64url-encoded, never in the clear", () => {
    const launch = "query_id=AA+x&auth_date=1&hash=ab/cd?";
    const [scheme, token] = protocolsFor(launch);

    expect(scheme).toBe("tma");
    expect(token).not.toMatch(/[+/=]/);
    expect(token).not.toContain("auth_date");
    const padded = token!.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (token!.length % 4)) % 4);
    expect(atob(padded)).toBe(launch);
  });
});

describe("reconnectDelayMs", () => {
  it("doubles from a second and stops at thirty", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 10].map((n) => reconnectDelayMs(n))).toEqual([
      1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000,
    ]);
  });
});
