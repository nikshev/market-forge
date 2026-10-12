// @trace: REQ-WP-101
// @trace: REQ-WP-092
// @trace: REQ-WP-086
//
// The lower pane as a chart of the same library, under the main one, on its time axis (PRD section 27.3).
//
// It used to be a 720 x 120 px SVG with its own time scale, no axis, no name and no crosshair: a shape a
// reader could not read and could not line up with a candle. This is a second chart instance, held to the
// first by three things: the same sequence of bar times (a whitespace backbone, so the library's index axis
// is the chart's), the same visible range and crosshair (subscribed both ways), and the same price-scale
// width and horizontal inset (so the plot areas begin and end together). What to draw is `paneChart.ts`'s.

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LogicalRange,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

import { findGaps, gapMarkers } from "./gaps";
import {
  backbone,
  PANE_HEIGHT,
  paneView,
  PRICE_SCALE_WIDTH,
  READING_INTERACTION,
  type ChartHandle,
} from "./paneChart";
import { toSeconds } from "./series";
import { chartLayout, type ChartPalette, type Scheme } from "./theme";
import type { BarOut, FeaturePointOut } from "./types";

const LINE_COLOUR = "#7c5cff";
const ZERO_COLOUR = "rgba(128, 128, 128, 0.6)";

const sameRange = (a: LogicalRange | null, b: LogicalRange | null): boolean =>
  a !== null && b !== null && Math.abs(a.from - b.from) < 1e-6 && Math.abs(a.to - b.to) < 1e-6;

export function PaneChart({
  chart,
  bars,
  feature,
  points,
  title,
  scheme,
  palette,
}: {
  chart: ChartHandle;
  bars: readonly BarOut[];
  feature: string;
  points: readonly FeaturePointOut[];
  title: string;
  scheme: Scheme;
  palette?: ChartPalette;
}): JSX.Element {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<IChartApi | null>(null);
  const crosshairSeries = useRef<ISeriesApi<"Line" | "Histogram"> | null>(null);
  // True while the reader's pointer is on the pane: only then is a range change on the pane the reader's.
  const reader = useRef(false);
  const view = useMemo(() => paneView(bars, feature, points), [bars, feature, points]);

  // The chart itself: one per scheme and palette.
  useEffect(() => {
    if (container.current === null) {
      return;
    }
    const created = createChart(container.current, {
      height: PANE_HEIGHT,
      autoSize: true,
      timeScale: { timeVisible: true, secondsVisible: false },
      // Margins keep the top and bottom axis labels inside a pane this short.
      rightPriceScale: { minimumWidth: PRICE_SCALE_WIDTH, scaleMargins: { top: 0.2, bottom: 0.1 } },
      // The same as the chart above it (REQ-WP-101): the wheel scrolls the page, the price axis stays on its auto-fit.
      handleScroll: READING_INTERACTION.handleScroll,
      handleScale: READING_INTERACTION.handleScale,
      ...chartLayout(scheme, palette),
    });
    instance.current = created;
    return () => {
      created.remove();
      instance.current = null;
    };
  }, [scheme, palette?.background, palette?.text, palette?.grid]);

  // What it draws: the whole bar sequence as a backbone, then the pane's series on top of it. Replaced, not
  // added to, on every change.
  useEffect(() => {
    const pane = instance.current;
    if (pane === null) {
      return;
    }
    const created: ISeriesApi<"Line" | "Histogram">[] = [];
    // Squares without text in the pane: the count is on the chart and in the notice, and in this short a pane the labels
    // would lie on top of each other.
    const gaps = gapMarkers(findGaps(bars), bars).map((mark) => ({ ...mark, text: "" }));

    const spine = pane.addLineSeries({
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    spine.setData(backbone(bars));
    created.push(spine);
    crosshairSeries.current = spine;

    if (view.kind === "histogram") {
      const histogram = pane.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceLineVisible: false,
        title,
      });
      histogram.setData(view.histogram);
      // The chart's gap markers, at the bars that have a value (REQ-WP-086): the pane must not contradict the chart.
      const here = gaps.filter((mark) => view.valueAt.has(mark.time as number));
      if (here.length > 0) {
        histogram.setMarkers(here);
      }
      created.push(histogram);
      crosshairSeries.current = histogram;
    } else {
      view.lines.forEach((line, index) => {
        const series = pane.addLineSeries({
          color: LINE_COLOUR,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: index === view.lines.length - 1,
          title: index === view.lines.length - 1 ? title : "",
        });
        series.setData(line);
        // A run is marked when its first point is at a gap marker's time, not by its number: a run also starts after a
        // trade-id break, where nothing is missing from the bars and no gap marker belongs.
        const starts = gaps.filter((mark) => mark.time === line[0]?.time);
        if (feature === "cvd_base" && starts.length > 0) {
          series.setMarkers(starts);
        }
        if (index === 0 && view.zeroLine) {
          series.createPriceLine({
            price: 0,
            color: ZERO_COLOUR,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: false,
            title: "",
          });
        }
        created.push(series);
        crosshairSeries.current = series;
      });
    }

    // Take the main chart's range now; it has already set it, and waiting for the next move would leave the
    // pane at its own until then.
    const range = chart.api.timeScale().getVisibleLogicalRange();
    if (range === null) {
      pane.timeScale().fitContent();
    } else {
      pane.timeScale().setVisibleLogicalRange(range);
    }

    return () => {
      // Not if the chart was removed first (unmount runs the other effect's cleanup before this one).
      if (instance.current === pane) {
        for (const series of created) {
          pane.removeSeries(series);
        }
      }
    };
  }, [bars, view, title, chart, scheme, palette?.background, palette?.text, palette?.grid]);

  // The main chart leads and the pane follows. The pane's range drives the main chart only while the reader is
  // moving the pane. A range the pane reports by itself is not the reader's: replacing its series makes the
  // library reset its range for a moment (to the empty chart's), and sending that to the main chart put it on
  // the first bars with an empty left edge, which is how this was found. The pane is put back to the chart's
  // range instead. Equal ranges stop an echo, whether the library reports a change at once or on the next frame.
  useEffect(() => {
    const pane = instance.current;
    if (pane === null) {
      return;
    }
    const mainScale = chart.api.timeScale();
    const paneScale = pane.timeScale();
    const onMain = (range: LogicalRange | null): void => {
      if (range !== null && !sameRange(range, paneScale.getVisibleLogicalRange())) {
        paneScale.setVisibleLogicalRange(range);
      }
    };
    const onPane = (range: LogicalRange | null): void => {
      if (range === null) {
        return;
      }
      const lead = mainScale.getVisibleLogicalRange();
      if (sameRange(range, lead)) {
        return;
      }
      if (reader.current) {
        mainScale.setVisibleLogicalRange(range);
      } else if (lead !== null) {
        paneScale.setVisibleLogicalRange(lead);
      }
    };

    const closeAt = new Map<number, number>(
      bars.map((bar) => [toSeconds(bar.close_time_ns) as number, Number(bar.close)]),
    );
    const onMainCrosshair = (param: MouseEventParams): void => {
      if (param.time === undefined) {
        pane.clearCrosshairPosition();
        return;
      }
      const series = crosshairSeries.current;
      if (series !== null) {
        pane.setCrosshairPosition(view.valueAt.get(param.time as number) ?? 0, param.time, series);
      }
    };
    const onPaneCrosshair = (param: MouseEventParams): void => {
      if (param.time === undefined) {
        chart.api.clearCrosshairPosition();
        return;
      }
      const candles = chart.candles();
      if (candles !== null) {
        chart.api.setCrosshairPosition(closeAt.get(param.time as number) ?? 0, param.time as Time, candles);
      }
    };

    mainScale.subscribeVisibleLogicalRangeChange(onMain);
    paneScale.subscribeVisibleLogicalRangeChange(onPane);
    chart.api.subscribeCrosshairMove(onMainCrosshair);
    pane.subscribeCrosshairMove(onPaneCrosshair);
    return () => {
      // The main chart may already be gone, and the pane's own removal runs first: neither may throw.
      try {
        mainScale.unsubscribeVisibleLogicalRangeChange(onMain);
        chart.api.unsubscribeCrosshairMove(onMainCrosshair);
      } catch {
        /* the main chart was removed first */
      }
      if (instance.current === pane) {
        paneScale.unsubscribeVisibleLogicalRangeChange(onPane);
        pane.unsubscribeCrosshairMove(onPaneCrosshair);
      }
    };
  }, [chart, bars, view, scheme, palette?.background, palette?.text, palette?.grid]);

  return (
    <Box
      sx={{ position: "relative" }}
      role="img"
      aria-label={`${feature} over ${view.count} point(s)`}
      onPointerEnter={() => {
        reader.current = true;
      }}
      onPointerLeave={() => {
        reader.current = false;
      }}
      onPointerCancel={() => {
        reader.current = false;
      }}
    >
      <Box sx={{ position: "absolute", top: 4, left: 8, zIndex: 2, pointerEvents: "none" }}>
        <Typography variant="caption" sx={{ fontWeight: 700 }}>
          {title}
          {view.last === undefined ? "" : `  ${view.last.toLocaleString("en", { maximumFractionDigits: 4 })}`}
        </Typography>
      </Box>
      <div ref={container} data-testid="pane-chart" />
    </Box>
  );
}
