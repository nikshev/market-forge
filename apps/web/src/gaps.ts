// @trace: REQ-WP-086
//
// A missing bar is visibly missing (PRD section 32: missing bars is a health metric of its own).
//
// The chart plots bars one after another on an index axis, so a hole in the series is drawn as no hole at all: two candles
// a week apart sit side by side with the channel, the extrema and the lower pane drawn across them. The axis is not
// changed here -- the lower pane lines up with it by index and the visible range is an index -- so the hole is *marked*
// where it is and *said in words*. A gap is found from two consecutive bars' own windows, so it cannot disagree with the
// bars; a bar that exists, whatever its volume, is never a gap (absence and quiet must not look alike).

import type { SeriesMarker, Time } from "lightweight-charts";

import { toSeconds } from "./series";
import type { BarOut } from "./types";

/** This feature's own marker colour: not the signal's, not the extrema's. */
export const GAP_COLOUR = "#f59f00";

/** How many gaps the notice lists before it counts the rest. */
export const NOTICE_LIMIT = 5;

export interface Gap {
  /** The close of the last bar before the hole. */
  afterCloseNs: bigint;
  /** The open of the first bar after it. */
  beforeOpenNs: bigint;
  /** How many bars of that window fit in between. */
  missing: number;
}

/** Gaps between consecutive bars, in time order. */
export function findGaps(bars: readonly BarOut[]): Gap[] {
  const ordered = [...bars].sort((a, b) =>
    a.open_time_ns < b.open_time_ns ? -1 : a.open_time_ns > b.open_time_ns ? 1 : 0,
  );
  const gaps: Gap[] = [];
  let previous: BarOut | null = null;
  for (const bar of ordered) {
    // A corrected bar has the same open as the one it replaces: not a new bar, so not a gap.
    if (previous !== null && bar.open_time_ns !== previous.open_time_ns) {
      const distance = bar.open_time_ns - previous.close_time_ns;
      const window = previous.close_time_ns - previous.open_time_ns;
      const missing = window > 0n ? Math.round(Number(distance) / Number(window)) : 0;
      if (distance > 0n && missing >= 1) {
        gaps.push({ afterCloseNs: previous.close_time_ns, beforeOpenNs: bar.open_time_ns, missing });
      }
    }
    previous = bar;
  }
  return gaps;
}

/** One marker per gap, at the first bar after it, stating how many are missing. */
export function gapMarkers(gaps: readonly Gap[], bars: readonly BarOut[]): SeriesMarker<Time>[] {
  const closeAfter = new Map(bars.map((bar) => [bar.open_time_ns, bar.close_time_ns]));
  const markers: SeriesMarker<Time>[] = [];
  for (const gap of gaps) {
    const close = closeAfter.get(gap.beforeOpenNs);
    if (close === undefined) {
      continue;
    }
    const time = toSeconds(close);
    markers.push({
      time,
      position: "aboveBar",
      shape: "square",
      color: GAP_COLOUR,
      text: `${gap.missing} missing`,
      id: `gap-${String(time)}`,
    });
  }
  return markers;
}

const two = (n: number): string => String(n).padStart(2, "0");

/** `DD.MM HH:mm`, UTC: the form the owner's own examples are written in. */
function stamp(ns: bigint): string {
  const date = new Date(Number(ns / 1_000_000n));
  return `${two(date.getUTCDate())}.${two(date.getUTCMonth() + 1)} ${two(date.getUTCHours())}:${two(date.getUTCMinutes())}`;
}

/** The facts a marker is too small to carry: how many, and over what span. */
export function describeGap(gap: Gap): string {
  const noun = gap.missing === 1 ? "bar" : "bars";
  return `${gap.missing} ${noun} missing, ${stamp(gap.afterCloseNs)} to ${stamp(gap.beforeOpenNs)}`;
}

/** The notice's lines: the most recent gaps first, at most `NOTICE_LIMIT`, then a count of the rest. */
export function noticeLines(gaps: readonly Gap[]): string[] {
  const recent = [...gaps].sort((a, b) => (a.beforeOpenNs < b.beforeOpenNs ? 1 : a.beforeOpenNs > b.beforeOpenNs ? -1 : 0));
  const lines = recent.slice(0, NOTICE_LIMIT).map(describeGap);
  return recent.length > NOTICE_LIMIT ? [...lines, `and ${recent.length - NOTICE_LIMIT} more`] : lines;
}
