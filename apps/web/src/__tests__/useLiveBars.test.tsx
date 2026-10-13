// @trace: REQ-WP-102
//
// The socket's lifecycle: it opens only for the 1m chart, subscribes, takes the snapshot and then the updates, says whether it is
// live, coalesces a burst of updates, reconnects with back-off, and closes when the page moves on.

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WireBar } from "../live";
import { useLiveBars } from "../useLiveBars";

class FakeSocket {
  static all: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(
    public url: string,
    public protocols?: string | string[],
  ) {
    FakeSocket.all.push(this);
  }
  send(text: string): void {
    this.sent.push(text);
  }
  close(): void {
    this.closed = true;
    this.readyState = 3;
  }
  open(): void {
    this.readyState = 1;
    this.onopen?.();
  }
  receive(message: unknown): void {
    this.onmessage?.({ data: typeof message === "string" ? message : JSON.stringify(message) });
  }
  drop(): void {
    this.readyState = 3;
    this.onclose?.();
  }
}

const MIN = 60_000_000_000n;
const T0 = 1_788_800_040_000_000_000n - (1_788_800_040_000_000_000n % MIN);
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
const snapshot = (...bars: WireBar[]) => ({ channel: "bars", data: { snapshot: bars } });
const update = (bar: WireBar) => ({ channel: "bars", data: { bar } });

const props = { venue: "bybit", symbol: "BTCUSDT", enabled: true };
const last = (): FakeSocket => FakeSocket.all.at(-1)!;

beforeEach(() => {
  vi.useFakeTimers();
  FakeSocket.all = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useLiveBars", () => {
  it("opens no socket and says off when the timeframe is not the live one", () => {
    const { result } = renderHook(() => useLiveBars({ ...props, enabled: false }));

    expect(FakeSocket.all).toHaveLength(0);
    expect(result.current).toEqual({ bars: [], status: "off" });
  });

  it("opens the gated socket on the page's host and subscribes to this series' bars at 1m once open", () => {
    renderHook(() => useLiveBars(props));

    expect(last().url).toBe("ws://localhost:3000/api/v1/live");
    expect(last().sent).toEqual([]);
    act(() => last().open());

    expect(JSON.parse(last().sent[0]!)).toEqual({
      op: "subscribe",
      venue: "bybit",
      symbol: "BTCUSDT",
      timeframe: "1m",
      channels: ["bars"],
    });
  });

  it("offers launch data as subprotocols, and none outside Telegram", () => {
    renderHook(() => useLiveBars({ ...props, launch: "auth_date=1&hash=ab" }));
    expect(last().protocols).toEqual(["tma", expect.not.stringContaining("auth_date")]);

    renderHook(() => useLiveBars({ ...props, launch: "" }));
    expect(last().protocols).toBeUndefined();
  });

  it("is delayed until the snapshot has arrived, then live with the cached bars", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive({ ok: true, live: true }));
    expect(result.current.status).toBe("delayed");

    act(() => last().receive(snapshot(wire(0, { is_final: true }), wire(1))));

    expect(result.current.status).toBe("live");
    expect(result.current.bars.map((b) => b.open_time_ns)).toEqual([T0, T0 + MIN]);
  });

  it("stays delayed, and does not reconnect in a loop, when the server says the feed is not live for it", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive({ ok: true, live: false }));
    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(result.current.status).toBe("delayed");
    expect(FakeSocket.all).toHaveLength(1);
  });

  it("applies updates: a forming bar becomes the final one and is never undone by a late forming bar", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));

    act(() => last().receive(update(wire(0, { close: "103", is_final: true }))));
    act(() => last().receive(update(wire(0, { close: "999" }))));
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.bars).toHaveLength(1);
    expect(result.current.bars[0]).toMatchObject({ close: "103", is_final: true });
  });

  it("coalesces a burst of updates into one state change", () => {
    let renders = 0;
    renderHook(() => {
      renders += 1;
      return useLiveBars(props);
    });
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));
    const before = renders;

    act(() => {
      for (let i = 0; i < 20; i += 1) {
        last().receive(update(wire(1, { close: String(100 + i) })));
      }
    });
    expect(renders).toBe(before);
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(renders).toBe(before + 1);
  });

  it("drops a frame it cannot read and goes on reading", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));

    act(() => last().receive("{{{"));
    act(() => last().receive(update(wire(1))));
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.bars).toHaveLength(2);
  });

  it("says delayed when the socket drops and reconnects after a second, then two, then four", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));

    act(() => last().drop());
    expect(result.current.status).toBe("delayed");
    expect(FakeSocket.all).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(FakeSocket.all).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeSocket.all).toHaveLength(2);

    act(() => last().drop());
    act(() => {
      vi.advanceTimersByTime(1999);
    });
    expect(FakeSocket.all).toHaveLength(2);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeSocket.all).toHaveLength(3);
  });

  it("starts the back-off over once a snapshot has been received again", () => {
    renderHook(() => useLiveBars(props));
    act(() => last().drop());
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => last().drop());
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));

    act(() => last().drop());
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(FakeSocket.all).toHaveLength(4);
  });

  it("keeps the bars it had while reconnecting, so the chart does not blank", () => {
    const { result } = renderHook(() => useLiveBars(props));
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0), wire(1))));

    act(() => last().drop());

    expect(result.current.bars).toHaveLength(2);
    expect(result.current.status).toBe("delayed");
  });

  it("closes the socket and does not reconnect when the page unmounts", () => {
    const { unmount } = renderHook(() => useLiveBars(props));
    const socket = last();
    act(() => socket.open());

    unmount();
    act(() => socket.drop());
    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(socket.closed).toBe(true);
    expect(FakeSocket.all).toHaveLength(1);
  });

  it("moves to the new series, forgetting the old one's bars, when the symbol changes", () => {
    const { result, rerender } = renderHook((p) => useLiveBars(p), { initialProps: props });
    act(() => last().open());
    act(() => last().receive(snapshot(wire(0))));
    const first = last();

    rerender({ ...props, symbol: "ETHUSDT" });

    expect(first.closed).toBe(true);
    expect(FakeSocket.all).toHaveLength(2);
    expect(result.current.bars).toEqual([]);
    act(() => last().open());
    expect(JSON.parse(last().sent[0]!).symbol).toBe("ETHUSDT");
  });

  it("closes when the timeframe stops being the live one", () => {
    const { result, rerender } = renderHook((p) => useLiveBars(p), { initialProps: props });
    const socket = last();
    act(() => socket.open());

    rerender({ ...props, enabled: false });

    expect(socket.closed).toBe(true);
    expect(result.current).toEqual({ bars: [], status: "off" });
  });

  it("ignores what an old socket says after it has been replaced", () => {
    const { result, rerender } = renderHook((p) => useLiveBars(p), { initialProps: props });
    const old = last();
    act(() => old.open());
    rerender({ ...props, symbol: "ETHUSDT" });
    act(() => last().open());

    act(() => old.receive(snapshot(wire(0))));
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.bars).toEqual([]);
  });
});
