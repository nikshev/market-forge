// @trace: REQ-WP-001
// @trace: REQ-WP-009
// @trace: REQ-US-002
//
// The page an alert's deep link opens. PRD section 27.1's route, and section
// 27.5's default: AS-SEEN-THEN, always, unless the link says otherwise in so
// many words.

import { useCallback, useEffect, useState } from "react";

import { fetchBars, fetchChannel, fetchExtrema, fetchFeatureSeries } from "./api";
import { Chart } from "./Chart";
import { ChannelModeControl } from "./ChannelMode";
import { FlowPane } from "./FlowPane";
import { LoadState, type LoadStateKind } from "./LoadState";
import { PANES } from "./panes";
import { parseDeepLink } from "./deepLink";
import { RESTORATION_NOTICE } from "./overlays";
import {
  AS_SEEN_THEN,
  type BarOut,
  type ChannelMode,
  type ChannelOut,
  type ExtremaResponse,
  type FeaturePointOut,
} from "./types";

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
  const [pane, setPane] = useState<string>(PANES[0]!.feature);
  const [points, setPoints] = useState<FeaturePointOut[]>([]);
  // A pane's own failure, kept apart from the page's: the chart can load while
  // the features do not, and one message for both would blame the wrong thing.
  const [paneFailure, setPaneFailure] = useState<string | null>(null);
  const [extrema, setExtrema] = useState<ExtremaResponse>({ confirmed: [], candidates: [] });

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

    const loaded = barsResult.value.bars;
    const seriesResult = await fetchFeatureSeries({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      startNs: loaded[0]?.open_time_ns ?? atNs,
      endNs: loaded.at(-1)?.close_time_ns ?? atNs,
    });
    setPaneFailure(seriesResult.ok ? null : seriesResult.error);
    setPoints(seriesResult.ok ? seriesResult.value.points : []);

    const extremaResult = await fetchExtrema({
      instrumentId: `${link.venue}:${link.symbol}`,
      timeframeNs,
      // AS-SEEN-THEN asks as of the instant; CURRENT REFIT asks for everything
      // on record, which is where PRD section 27.5 wants the difference to show.
      asOfNs: mode === AS_SEEN_THEN ? atNs : null,
    });
    // An absent list is not a failure of the page, the way an absent channel is
    // not: the chart draws what it has.
    setExtrema(extremaResult.ok ? extremaResult.value : { confirmed: [], candidates: [] });
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

  // Said out loud, never inferred from an empty chart: a page that quietly
  // showed its defaults would claim to have restored a state nobody recorded.
  const notice = RESTORATION_NOTICE[link.overlays.state];

  return (
    <main>
      <h1>ChannelFlow</h1>
      <h2>
        {link.symbol} · {link.venue} · {link.timeframe}
      </h2>
      <ChannelModeControl mode={mode} onChange={setMode} />
      <LoadState state={state} detail={detail} />
      {notice === null ? null : (
        // Named, because the page now carries more than one status and a
        // reader -- or a test -- asking for "the status" would get whichever
        // came first.
        <p role="status" aria-label="Overlay restoration">
          {notice}
        </p>
      )}
      <Chart
        bars={bars}
        channel={channel}
        signal={null}
        overlays={link.overlays.overlays}
        focusAtNs={link.atNs}
        extrema={extrema}
        mode={mode}
      />
      <FlowPane points={points} feature={pane} onSelect={setPane} failure={paneFailure} />
    </main>
  );
}
