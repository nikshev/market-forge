// @trace: REQ-WP-092
// @trace: REQ-WP-101
//
// The lower pane as a chart on the main chart's own time axis: the decisions, kept pure so they can be tested.
//
// lightweight-charts' time axis is an index over the union of the times its series hold, so two charts line up
// only if they hold the same sequence of times. That is what everything here is for: a bar without a value is a
// whitespace entry and not an absent one, a value goes to the bar whose window contains its instant and never
// to a slot of its own, and a CVD run is its own series so that nothing is joined across a break. The drawing
// is `PaneChart.tsx`'s; the library cannot be laid out under jsdom, so what is asserted is what it is handed.

import type { IChartApi, ISeriesApi, Time } from "lightweight-charts";

import { paneSeries, segments } from "./panes";
import type { PanePoint } from "./panes";
import { toSeconds } from "./series";
import type { BarOut, FeaturePointOut } from "./types";

/** Both charts' right price scales are at least this wide, so their plot areas start and end together. */
export const PRICE_SCALE_WIDTH = 88;
export const PANE_HEIGHT = 160;

/**
 * What a reader may do to a chart (REQ-WP-101). A chart here is read, not operated: with the library's defaults the
 * mouse wheel zooms the time axis, so scrolling the page with the pointer over a chart stopped the page and squeezed and
 * stretched the chart instead; and a drag on the price axis switches its auto-fit off, leaving a scale nobody chose.
 * Dragging along the time axis, dragging the plot and pinching stay.
 */
export const READING_INTERACTION = {
  handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
  handleScale: {
    mouseWheel: false,
    pinch: true,
    axisPressedMouseMove: { time: true, price: false },
  },
} as const;

/** The main chart's price scale leaves this share of the plot above and below the candles (the library's default is 20 % and 10 %). */
export const PLOT_MARGINS = { top: 0.08, bottom: 0.08 } as const;

/** The candle's own colours (lightweight-charts' defaults), so a volume bar is the colour of its candle. */
export const UP_COLOUR = "#26a69a";
export const DOWN_COLOUR = "#ef5350";

/** What the main chart gives a pane that must line up with it. `candles` is a getter: the series is replaced as data changes. */
export interface ChartHandle {
  api: IChartApi;
  candles: () => ISeriesApi<"Candlestick"> | null;
}

export interface AlignedPoint {
  time: Time;
  value?: number;
}

export interface VolumeBar extends AlignedPoint {
  color?: string;
}

const closeSeconds = (bar: BarOut): Time => toSeconds(bar.close_time_ns);

function inCloseOrder(bars: readonly BarOut[]): BarOut[] {
  return [...bars].sort((a, b) =>
    a.close_time_ns < b.close_time_ns ? -1 : a.close_time_ns > b.close_time_ns ? 1 : 0,
  );
}

/** The index of the bar whose window `(open, close]` holds the instant, or -1. */
function barIndexFor(sorted: readonly BarOut[], at: bigint): number {
  let low = 0;
  let high = sorted.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (sorted[middle]!.close_time_ns >= at) {
      found = middle;
      high = middle - 1;
    } else {
      low = middle + 1;
    }
  }
  return found !== -1 && at > sorted[found]!.open_time_ns ? found : -1;
}

/**
 * One entry per bar, at the candle's time; a value where one lands in the bar, whitespace where none does.
 *
 * A value belongs to the bar whose window is `(open, close]`: one stamped exactly at a bar's close is that
 * bar's, because the flow features are stamped at the close of the bar they describe and would otherwise land
 * on the next one. (A trade at a boundary is the *later* bar's; this is a different thing -- a value computed
 * at an instant, not an event inside a window -- and a test pins both.) Two values in one bar show the later.
 * A value no bar contains gets no entry: inventing a slot would shift every index after it.
 */
export function alignToBars(bars: readonly BarOut[], points: readonly PanePoint[]): AlignedPoint[] {
  const sorted = inCloseOrder(bars);
  const values: (number | undefined)[] = new Array<number | undefined>(sorted.length).fill(undefined);
  const ordered = [...points].sort((a, b) => (a.at_ns < b.at_ns ? -1 : a.at_ns > b.at_ns ? 1 : 0));
  for (const point of ordered) {
    const index = barIndexFor(sorted, point.at_ns);
    if (index !== -1) {
      values[index] = point.value;
    }
  }
  return sorted.map((bar, index) => {
    const value = values[index];
    return value === undefined ? { time: closeSeconds(bar) } : { time: closeSeconds(bar), value };
  });
}

/** One value-only series per run. They carry no whitespace: the chart's backbone already holds every time. */
export function lineRuns(
  bars: readonly BarOut[],
  parts: readonly (readonly PanePoint[])[],
): { time: Time; value: number }[][] {
  return parts.map((part) =>
    alignToBars(bars, part).filter((p): p is { time: Time; value: number } => p.value !== undefined),
  );
}

/** Volume per bar, coloured by the candle's direction; a forming bar or a bad value is whitespace. */
export function volumeBars(bars: readonly BarOut[]): VolumeBar[] {
  return inCloseOrder(bars).map((bar) => {
    const time = closeSeconds(bar);
    const value = Number(bar.volume_base);
    if (!bar.is_final || bar.volume_base.trim() === "" || !Number.isFinite(value)) {
      return { time };
    }
    return { time, value, color: Number(bar.close) >= Number(bar.open) ? UP_COLOUR : DOWN_COLOUR };
  });
}

/** Every bar time, with nothing to draw: what holds a chart's axis to the bars' sequence. */
export function backbone(bars: readonly BarOut[]): { time: Time }[] {
  return inCloseOrder(bars).map((bar) => ({ time: closeSeconds(bar) }));
}

export interface PaneView {
  kind: "histogram" | "lines";
  histogram: VolumeBar[];
  lines: AlignedPoint[][];
  /** The value drawn at each candle time, for the crosshair. */
  valueAt: Map<number, number>;
  /** How many values are drawn, for the pane's accessible name. */
  count: number;
  last: number | undefined;
  zeroLine: boolean;
}

/** What to draw for one pane, from the bars and the feature series. */
export function paneView(
  bars: readonly BarOut[],
  feature: string,
  points: readonly FeaturePointOut[],
): PaneView {
  const valueAt = new Map<number, number>();
  const remember = (drawn: readonly AlignedPoint[]): void => {
    for (const p of drawn) {
      if (p.value !== undefined) {
        valueAt.set(p.time as number, p.value);
      }
    }
  };

  if (feature === "volume") {
    const histogram = volumeBars(bars);
    remember(histogram);
    const values = histogram.filter((p) => p.value !== undefined);
    return {
      kind: "histogram",
      histogram,
      lines: [],
      valueAt,
      count: values.length,
      last: values.at(-1)?.value,
      zeroLine: false,
    };
  }

  const series = paneSeries(points, feature);
  // CVD is a running sum within a run; each run is a series of its own so no line joins two (REQ-WP-088).
  const lines =
    feature === "cvd_base"
      ? lineRuns(bars, segments(series.points, points))
      : [alignToBars(bars, series.points)];
  for (const line of lines) {
    remember(line);
  }
  const last = [...valueAt.entries()].sort((a, b) => a[0] - b[0]).at(-1)?.[1];
  return {
    kind: "lines",
    histogram: [],
    lines,
    valueAt,
    count: series.points.length,
    last,
    zeroLine: feature === "cvd_base",
  };
}
