// @trace: REQ-WP-102
//
// The chart's socket (REQ-WP-102): open only while the timeframe is the live one, subscribe to the series' 1m bars, keep the
// bars it hears, and say whether the chart is **live** or **delayed**. What the messages mean is `live.ts`'s.
//
// A burst of updates is coalesced -- a busy market sends one forming bar a second, and the chart needs the latest of them,
// not a render for each. The bars it holds survive a dropped connection (a chart that blanked every time a proxy
// restarted would look broken, not delayed), and a socket that has been replaced is ignored. It reconnects with
// back-off, and the periodic reload the page already has keeps the chart current meanwhile.

import { useEffect, useRef, useState } from "react";

import { LIVE_TIMEFRAME, applyBar, parseMessage, protocolsFor, reconnectDelayMs, socketUrl, type LiveStatus } from "./live";
import { launchData } from "./telegram";
import type { BarOut } from "./types";

/** How long a burst of updates is gathered before the page is told. */
export const COALESCE_MS = 250;

export interface LiveBars {
  bars: BarOut[];
  status: LiveStatus;
}

export function useLiveBars({
  venue,
  symbol,
  enabled,
  launch = launchData(),
  apiBase = import.meta.env.VITE_API_BASE ?? "",
}: {
  venue: string;
  symbol: string;
  enabled: boolean;
  /** The Telegram launch data, offered as the socket's subprotocols; empty outside Telegram. */
  launch?: string;
  apiBase?: string;
}): LiveBars {
  const [bars, setBars] = useState<BarOut[]>([]);
  const [status, setStatus] = useState<LiveStatus>(enabled ? "delayed" : "off");
  // What the socket has heard, outside render: updates land here at once and reach the page on a timer.
  const heard = useRef<BarOut[]>([]);

  useEffect(() => {
    heard.current = [];
    setBars([]);
    if (!enabled) {
      setStatus("off");
      return undefined;
    }
    setStatus("delayed");

    let disposed = false;
    let socket: WebSocket | null = null;
    let attempt = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let flush: ReturnType<typeof setTimeout> | undefined;

    const publish = (): void => {
      flush = undefined;
      setBars(heard.current);
    };
    const schedulePublish = (): void => {
      if (flush === undefined) {
        flush = setTimeout(publish, COALESCE_MS);
      }
    };

    const connect = (): void => {
      const protocols = protocolsFor(launch);
      const mine = protocols.length === 0 ? new WebSocket(socketUrl(window.location, apiBase)) : new WebSocket(socketUrl(window.location, apiBase), protocols);
      socket = mine;
      const current = (): boolean => !disposed && socket === mine;

      mine.onopen = () => {
        if (current()) {
          mine.send(JSON.stringify({ op: "subscribe", venue, symbol, timeframe: LIVE_TIMEFRAME, channels: ["bars"] }));
        }
      };
      mine.onmessage = (event: MessageEvent<string>) => {
        if (!current()) {
          return;
        }
        const message = parseMessage(String(event.data));
        if (message === null) {
          return;
        }
        if (message.kind === "snapshot") {
          for (const bar of message.bars) {
            heard.current = applyBar(heard.current, bar);
          }
          attempt = 0;
          setStatus("live");
          publish();
        } else if (message.kind === "bar") {
          heard.current = applyBar(heard.current, message.bar);
          schedulePublish();
        }
      };
      const lost = (): void => {
        if (!current()) {
          return;
        }
        setStatus("delayed");
        retry = setTimeout(() => {
          retry = undefined;
          if (!disposed) {
            connect();
          }
        }, reconnectDelayMs(attempt));
        attempt += 1;
      };
      mine.onclose = lost;
      mine.onerror = () => undefined; // a failed connection is followed by `close`, which is what retries
    };

    connect();
    return () => {
      disposed = true;
      if (retry !== undefined) {
        clearTimeout(retry);
      }
      if (flush !== undefined) {
        clearTimeout(flush);
      }
      socket?.close();
      socket = null;
    };
  }, [venue, symbol, enabled, launch, apiBase]);

  return enabled ? { bars, status } : { bars: [], status: "off" };
}
