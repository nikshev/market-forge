// @trace: REQ-WP-080
// @trace: REQ-WP-009
// @trace: REQ-US-002
// @trace: REQ-WP-084
// @trace: REQ-WP-092
// @trace: REQ-WP-086
//
// PRD section 27.2's overlays, for the four layers REQ-WP-009's acceptance
// names: candles, the channel's centre and boundaries, the setup zones, and a
// marker at the signal.
//
// The decision about *what* to draw lives in `series.ts`, where it can be
// tested; this attaches it to the library. jsdom cannot lay out a container,
// so a component test here would assert nothing about the picture -- which is
// why the split exists.

import { createChart, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { extremumMarkers } from "./extrema";
import { findGaps, gapMarkers } from "./gaps";
import { PRICE_SCALE_WIDTH, type ChartHandle } from "./paneChart";
import { buildSeries, markerFor, toSeconds, visibleRangeFor, CHANNEL_STYLE, visibleRangeForChannel } from "./series";
import { AS_SEEN_THEN, DEFAULT_OVERLAYS } from "./types";
import type {
  BarOut,
  ChannelMode,
  ChannelOut,
  ExtremaResponse,
  Overlay,
  SignalOut,
} from "./types";
import { profileBars } from "./volumeProfile";
import { chartLayout, schemeNow, type ChartPalette, type Scheme } from "./theme";
import type { Profile } from "./volumeProfile";

const ZONE_COLOURS: Record<string, string> = {
  upper: "rgba(214, 69, 69, 0.10)",
  middle: "rgba(120, 120, 120, 0.08)",
  lower: "rgba(47, 158, 68, 0.10)",
};

// How many bars the deep link's instant is centred in. Wide enough to read the
// setup's context, narrow enough that the bar the alert is about is obvious.
const FOCUS_SPAN = 60;

export function Chart({
  bars,
  channel,
  signal,
  profile = null,
  overlays = DEFAULT_OVERLAYS,
  focusAtNs = null,
  extrema = { confirmed: [], candidates: [] },
  showCandidates = false,
  mode = AS_SEEN_THEN,
  scheme = schemeNow(),
  palette,
  onReady,
}: {
  bars: BarOut[];
  channel: ChannelOut | null;
  signal: SignalOut | null;
  profile?: Profile | null;
  overlays?: readonly Overlay[];
  focusAtNs?: bigint | null;
  extrema?: ExtremaResponse;
  /** Candidate extrema are unconfirmed turns; they are drawn only when asked (REQ-WP-084). */
  showCandidates?: boolean;
  /** Which mode the chart is in. The extremum filter is AS-SEEN-THEN's only. */
  mode?: ChannelMode;
  /** The colour scheme (REQ-WP-080). Light is what the chart always was. */
  scheme?: Scheme;
  /** The interface's colours, so the canvas sits on the surface it is drawn on (REQ-WP-083). */
  palette?: ChartPalette;
  /**
   * Gives a pane under the chart what it needs to line up with it (REQ-WP-092): the chart, and a getter for the
   * current candle series, which is replaced as the data changes. `null` when the chart goes away.
   */
  onReady?: (handle: ChartHandle | null) => void;
}): JSX.Element {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candlesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  useEffect(() => {
    if (container.current === null) {
      return;
    }
    const instance = createChart(container.current, {
      height: 480,
      // Follow the container's width, so the chart fits a phone and a resized window (REQ-WP-083).
      autoSize: true,
      timeScale: { timeVisible: true, secondsVisible: false },
      // The same minimum width as the pane under it, so the two plot areas begin and end together.
      rightPriceScale: { minimumWidth: PRICE_SCALE_WIDTH },
      ...chartLayout(scheme, palette),
    });
    chart.current = instance;
    onReadyRef.current?.({ api: instance, candles: () => candlesRef.current });
    return () => {
      onReadyRef.current?.(null);
      instance.remove();
      chart.current = null;
    };
  }, [scheme, palette?.background, palette?.text, palette?.grid]);

  useEffect(() => {
    const instance = chart.current;
    if (instance === null) {
      return;
    }
    const { candles, channelLines, zones } = buildSeries({ bars, channel });
    // Exactly the layers the link named (REQ-US-002). A chart that draws more
    // than the alert had on is showing a different picture from the one the
    // setup was judged against, and saying nothing about the difference.
    const on = new Set(overlays);

    // Every series this run creates, so the next run (and an unmount) can take them away. The effect
    // runs again each time its data changes -- bars, then the channel, then the extrema -- and without this
    // each run left its candles, lines and markers on the chart beside the next run's.
    const created: ISeriesApi<"Candlestick" | "Line">[] = [];
    const candlestick = instance.addCandlestickSeries();
    created.push(candlestick);
    candlesRef.current = candlestick;
    // With the candles layer off the series still holds every bar time, as whitespace: the pane under the chart
    // lines up by index, and its axis must not depend on which layers are on (REQ-WP-092).
    candlestick.setData(on.has("candles") ? candles : candles.map((candle) => ({ time: candle.time })));

    // One `setMarkers` call: lightweight-charts replaces the whole set, so a
    // second call for the extrema would silently drop the signal's marker.
    const marks = [
      ...(signal !== null && on.has("signal_marker") ? [markerFor(signal, channel)] : []),
      ...extremumMarkers({
        confirmed: extrema.confirmed,
        candidates: extrema.candidates,
        includeCandidates: showCandidates,
        mode,
        atNs: focusAtNs ?? bars.at(-1)?.close_time_ns ?? 0n,
      }).map((mark) => ({
        time: toSeconds(mark.at_ns),
        position: mark.type === "HIGH" ? ("aboveBar" as const) : ("belowBar" as const),
        // A confirmation is filled and a candidate is hollow: the same glyph
        // in two weights, so a reader sees one alphabet rather than two.
        shape: mark.type === "HIGH" ? ("arrowDown" as const) : ("arrowUp" as const),
        color: mark.kind === "confirmed" ? "#2f9e44" : "#adb5bd",
        text: mark.kind === "confirmed" ? "" : "?",
      })),
    ];
    // A hole in the bars is marked where it is (REQ-WP-086), in the same call and in time order: the library replaces
    // the whole set, so a second call would drop the others.
    const allMarks = [...marks, ...gapMarkers(findGaps(bars), bars)].sort(
      (a, b) => (a.time as number) - (b.time as number),
    );
    if (allMarks.length > 0) {
      candlestick.setMarkers(allMarks);
    }

    for (const [name, points] of Object.entries(channelLines)) {
      if (!on.has(name === "center" ? "channel_center" : "channel_bounds")) {
        continue;
      }
      const style = CHANNEL_STYLE[name as keyof typeof CHANNEL_STYLE];
      const line = instance.addLineSeries({
        ...style,
        priceLineVisible: false,
        title: name,
      });
      line.setData(points);
      created.push(line);
    }

    // Zones are drawn as price lines rather than filled areas: the library has
    // no band primitive, and faking one with two stacked areas would put a
    // shape on the chart whose edges do not mean what they look like.
    for (const [name, band] of Object.entries(on.has("signal_zones") ? zones : {})) {
      for (const edge of [band.from, band.to]) {
        candlestick.createPriceLine({
          price: edge,
          color: ZONE_COLOURS[name] ?? "rgba(120,120,120,0.1)",
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: false,
          title: `${name} zone`,
        });
      }
    }

    // PRD section 27.2's volume profile overlay. lightweight-charts has no
    // horizontal-histogram primitive, so each bin is a price line whose title
    // carries its relative width -- the profile's shape read as labels rather
    // than drawn as bars. A faked histogram out of stacked areas would put
    // edges on the chart that do not mean what they look like, the same
    // reasoning the channel zones follow.
    for (const bar of profileBars(on.has("volume_profile") ? profile : null)) {
      candlestick.createPriceLine({
        price: (bar.low + bar.high) / 2,
        color:
          bar.role === "poc"
            ? "#e8590c"
            : bar.role === "value-area"
              ? "rgba(232, 89, 12, 0.35)"
              : "rgba(120, 120, 120, 0.2)",
        lineWidth: bar.role === "poc" ? 2 : 1,
        lineStyle: 0,
        axisLabelVisible: bar.role === "poc",
        title: `${bar.role} ${(bar.width * 100).toFixed(0)}%`,
      });
    }

    const range = visibleRangeFor(bars, focusAtNs, FOCUS_SPAN);
    if (range === null) {
      // No instant named and a channel: open on its window so it fills the view (REQ-WP-082). Otherwise
      // fit everything, as before.
      const recent =
        focusAtNs === null && channel !== null ? visibleRangeForChannel(bars, channel.lookback) : null;
      if (recent === null) {
        instance.timeScale().fitContent();
      } else {
        instance.timeScale().setVisibleLogicalRange(recent);
      }
    } else {
      // REQ-US-002: "opens the chart at exactly the signal's timestamp".
      instance.timeScale().setVisibleLogicalRange(range);
    }
    return () => {
      if (candlesRef.current === candlestick) {
        candlesRef.current = null;
      }
      // Not if the chart itself was removed first (unmount runs the other effect's cleanup before this one,
      // and removing a series from a disposed chart throws). Price lines go with their series.
      if (chart.current === instance) {
        for (const series of created) {
          instance.removeSeries(series);
        }
      }
    };
  }, [bars, channel, signal, profile, overlays, focusAtNs, extrema, showCandidates, mode]);

  return <div ref={container} data-testid="chart" />;
}
