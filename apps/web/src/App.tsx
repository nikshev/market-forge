// @trace: REQ-WP-001
// @trace: REQ-WP-009
//
// The page an alert's deep link opens. PRD section 27.1's route, and section
// 27.5's default: AS-SEEN-THEN, always, unless the link says otherwise in so
// many words.

import { useCallback, useEffect, useState } from "react";

import { fetchBars, fetchChannel } from "./api";
import { Chart } from "./Chart";
import { ChannelModeControl } from "./ChannelMode";
import { LoadState, type LoadStateKind } from "./LoadState";
import { parseDeepLink } from "./deepLink";
import { AS_SEEN_THEN, type BarOut, type ChannelMode, type ChannelOut } from "./types";

const MINUTE_NS = 60 * 1_000_000_000;

export function App(): JSX.Element {
  const link =
    typeof window === "undefined"
      ? null
      : parseDeepLink(window.location.pathname, window.location.search);

  const [mode, setMode] = useState<ChannelMode>(link?.mode ?? AS_SEEN_THEN);
  const [bars, setBars] = useState<BarOut[]>([]);
  const [channel, setChannel] = useState<ChannelOut | null>(null);
  const [state, setState] = useState<LoadStateKind>("ok");
  const [detail, setDetail] = useState<string | undefined>(undefined);

  const load = useCallback(async () => {
    if (link === null) {
      return;
    }
    const timeframeNs = 15 * MINUTE_NS;
    const barsResult = await fetchBars({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      limit: 500,
    });
    if (!barsResult.ok) {
      // FR-016: a failed load is stated, never rendered as an empty chart that
      // could be mistaken for a quiet market.
      setState("failed");
      setDetail(barsResult.error);
      return;
    }
    setBars(barsResult.value.bars);
    setState(barsResult.value.bars.length === 0 ? "empty" : "ok");

    const atNs = link.atNs ?? barsResult.value.bars.at(-1)?.close_time_ns ?? null;
    if (atNs === null) {
      return;
    }
    const channelResult = await fetchChannel({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      atNs,
      mode,
    });
    // An absent channel is not a failure of the page: the chart draws candles
    // and no channel, which is the honest picture (US4 scenario 5).
    setChannel(channelResult.ok ? channelResult.value : null);
  }, [link, mode]);

  useEffect(() => {
    void load();
  }, [load]);

  if (link === null) {
    return (
      <main>
        <h1>ChannelFlow</h1>
        <p>Open a chart at /chart/&lt;venue&gt;/&lt;symbol&gt;.</p>
      </main>
    );
  }

  return (
    <main>
      <h1>ChannelFlow</h1>
      <h2>
        {link.symbol} · {link.venue} · {link.timeframe}
      </h2>
      <ChannelModeControl mode={mode} onChange={setMode} />
      <LoadState state={state} detail={detail} />
      <Chart bars={bars} channel={channel} signal={null} />
    </main>
  );
}
