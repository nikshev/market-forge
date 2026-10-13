// @trace: REQ-WP-101
// @trace: REQ-WP-102
// @trace: REQ-WP-080
// @trace: REQ-WP-009
// @trace: REQ-US-002
// @trace: REQ-WP-084
// @trace: REQ-WP-092
// @trace: REQ-WP-086
// @trace: REQ-WP-089
// @trace: REQ-WP-090
// @trace: REQ-WP-091
//
// PRD section 27.2's overlays, for the four layers REQ-WP-009's acceptance
// names: candles, the channel's centre and boundaries, the setup zones, and a
// marker at the signal -- plus REQ-WP-091's optional consensus line over them.
//
// The decision about *what* to draw lives in `series.ts`, where it can be
// tested; this attaches it to the library. jsdom cannot lay out a container,
// so a component test here would assert nothing about the picture -- which is
// why the split exists.

import { createChart, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { extremumMarkers } from "./extrema";
import { findGaps, gapMarkers } from "./gaps";
import { liveAfter } from "./live";
import { PLOT_MARGINS, PRICE_SCALE_WIDTH, CHART_INTERACTION, type ChartHandle } from "./paneChart";
import {
  buildSeries,
  markerFor,
  toSeconds,
  visibleRangeFor,
  CHANNEL_STYLE,
  visibleRangeForChannel,
  type Candle,
} from "./series";
import { AS_SEEN_THEN, DEFAULT_OVERLAYS } from "./types";
import type {
  BarOut,
  ChannelMode,
  ChannelOut,
  ConsensusPointOut,
  ExtremaResponse,
  Overlay,
  SignalOut,
  VolumeProfileOut,
} from "./types";
import { ProfilePrimitive } from "./profilePrimitive";
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

// Stable empties, so a chart given no live bars or no extrema does not see a new prop on every render -- which
// re-ran the data effect, and with it every series and overlay, whenever the parent re-rendered.
const NO_EXTREMA: ExtremaResponse = { confirmed: [], candidates: [] };
const NO_LIVE_BARS: readonly BarOut[] = [];

/** The candles as drawn: the stored ones, then the live bars after them (whitespace when the candles layer is off). */
function drawn(stored: readonly BarOut[], live: readonly BarOut[], candlesOn: boolean): Candle[] | { time: Time }[] {
  const all = [...buildSeries({ bars: [...stored], channel: null }).candles, ...buildSeries({ bars: liveAfter(stored, live), channel: null }).candles];
  return candlesOn ? all : all.map((candle) => ({ time: candle.time }));
}

export function Chart({
  bars,
  channel,
  signal = null,
  profile = null,
  volumeProfile = null,
  consensus = null,
  overlays = DEFAULT_OVERLAYS,
  focusAtNs = null,
  extrema = NO_EXTREMA,
  showCandidates = false,
  mode = AS_SEEN_THEN,
  scheme = schemeNow(),
  palette,
  onReady,
  isInitialLoad = true,
  liveBars = NO_LIVE_BARS,
}: {
  bars: BarOut[];
  channel: ChannelOut | null;
  signal: SignalOut | null;
  profile?: Profile | null;
  /** The profile by price level with the buy/sell split, drawn at the side of the chart (REQ-WP-089). */
  volumeProfile?: VolumeProfileOut | null;
  /**
   * The cross-venue consensus, one point per bar (REQ-WP-091): the median mid where at least two
   * venues contributed, the refusal reason where they did not -- the `consensus` array of a
   * `ConsensusOut`. `null` (the default) draws nothing and says nothing; the line itself is a
   * layer, so it is drawn only when `overlays` names it.
   */
  consensus?: ConsensusPointOut[] | null;
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
  /** True for initial load (mount or timeframe/mode change), false for timer refresh (REQ-WP-090). */
  isInitialLoad?: boolean;
  /**
   * The bars the live feed holds (REQ-WP-102): drawn after the last stored one, updated in place without
   * recreating the chart or touching the reader's range. A stored bar supersedes the live one for its minute.
   */
  liveBars?: readonly BarOut[];
}): JSX.Element {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candlesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;
  // What the live effect needs of the data effect, which owns the series: the stored bars and whether candles are on.
  const liveRef = useRef(liveBars);
  liveRef.current = liveBars;
  const storedRef = useRef<{ bars: BarOut[]; candlesOn: boolean }>({ bars: [], candlesOn: true });

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
      rightPriceScale: { minimumWidth: PRICE_SCALE_WIDTH, autoScale: true, scaleMargins: PLOT_MARGINS },
      // Read, not operated (REQ-WP-101): the wheel scrolls the page, and the price axis stays on its auto-fit.
      handleScroll: CHART_INTERACTION.handleScroll,
      handleScale: CHART_INTERACTION.handleScale,
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
    const { channelLines, zones } = buildSeries({ bars, channel });
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
    storedRef.current = { bars, candlesOn: on.has("candles") };
    // The stored candles plus the live bars after them (REQ-WP-102): the live effect keeps them current, and
    // this redraws them when the stored bars are reloaded.
    candlestick.setData(drawn(bars, liveRef.current, on.has("candles")));

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

    // REQ-WP-091 (PRD §17.1): the cross-venue consensus mid as one violet line over the candles.
    // A bar whose consensus was refused has no point, so the library breaks the line there -- the
    // gap *is* the refusal, never a one-venue "consensus" stretched across it. The gap's reason is
    // said beside the chart (below), not written into the line.
    if (on.has("consensus") && consensus !== null) {
      const line = instance.addLineSeries({
        // Violet, distinct from the channel's centre (#7c5cff) so the two never read as one line.
        color: "#7048e8",
        lineWidth: 2,
        lineStyle: 0,
        priceLineVisible: false,
        title: "consensus",
      });
      line.setData(
        consensus
          .filter((point): point is ConsensusPointOut & { consensus_mid: string } => point.consensus_mid !== null)
          .map((point) => ({ time: toSeconds(point.bar_close_ns), value: Number(point.consensus_mid) })),
      );
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

    // REQ-WP-089: the profile by price level, a primitive on the candle series so it follows the chart's price scale.
    const primitive = on.has("volume_profile") && volumeProfile !== null ? new ProfilePrimitive(volumeProfile) : null;
    if (primitive !== null) {
      candlestick.attachPrimitive(primitive);
    }

    const range = visibleRangeFor(bars, focusAtNs, FOCUS_SPAN);
    // REQ-WP-090: only set the visible range on initial load (mount or timeframe/mode change).
    // On refresh (isInitialLoad=false), the library keeps the reader's pan/zoom.
    if (isInitialLoad) {
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
    }
    return () => {
      if (candlesRef.current === candlestick) {
        candlesRef.current = null;
      }
      // Not if the chart itself was removed first (unmount runs the other effect's cleanup before this one,
      // and removing a series from a disposed chart throws). Price lines go with their series.
      if (chart.current === instance) {
        if (primitive !== null) {
          candlestick.detachPrimitive(primitive);
        }
        for (const series of created) {
          instance.removeSeries(series);
        }
      }
    };
  }, [bars, channel, signal, profile, volumeProfile, consensus, overlays, focusAtNs, extrema, showCandidates, mode]);

  // REQ-WP-102: the live bars change the candle series' data in place. Not the data effect above: that one
  // recreates every series, overlay and marker, and would reset what the reader has zoomed to on each tick.
  useEffect(() => {
    const series = candlesRef.current;
    if (series === null) {
      return;
    }
    series.setData(drawn(storedRef.current.bars, liveBars, storedRef.current.candlesOn));
  }, [liveBars]);

  // REQ-WP-091 / FR-004: the gap in the line is not silent. The distinct reasons the consensus was
  // refused in the data on screen, said once each beside the chart -- only while the layer is on
  // and only when there is something to say, so a complete consensus (or none at all) adds no notice.
  const refusalReasons = [
    ...new Set(
      (consensus ?? [])
        .map((point) => point.refusal_reason)
        .filter((reason): reason is string => reason !== null),
    ),
  ];
  const notice =
    overlays.includes("consensus") && refusalReasons.length > 0 ? (
      <div role="status">Consensus not drawn for every bar: {refusalReasons.join(", ")}</div>
    ) : null;

  return (
    <>
      <div ref={container} data-testid="chart" />
      {notice}
    </>
  );
}
