// @trace: REQ-WP-083
// @trace: REQ-WP-009
// @trace: REQ-WP-082
// @trace: REQ-WP-108
//
// What the chart draws, decided here rather than inside a component.
//
// `lightweight-charts` needs a laid-out container to render, which jsdom does
// not provide -- so a component test can never see a candle. Extracting the
// decision means the part that can be wrong is the part that is tested: which
// candles, which lines, which bands, and where the marker sits.

import type { Time } from "lightweight-charts";

import { ZONES } from "./types";
import { chartSeconds } from "./time";
import type { BarOut, ChannelOut, SignalOut } from "./types";

// `Time` rather than `number`: lightweight-charts accepts a UNIX second, a
// business day or a date string, and its own type is what keeps a caller from
// passing nanoseconds -- which it would happily plot in the year 58,000.
export interface Candle {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LinePoint {
  time: Time;
  value: number;
}

export interface Band {
  from: number;
  to: number;
}

export interface Marker {
  time: Time;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowDown" | "arrowUp";
  text: string;
}

// How the channel's lines look (REQ-WP-082). The first version was grey, thin and dashed, and the owner
// wrote "I do not see the channel". The centre is solid and heavy; the bounds take the zones' own colours
// (upper is where a short is rejected, so red), so a line and the zone it bounds read as one thing.
export const CHANNEL_STYLE = {
  center: { color: "#7c5cff", lineWidth: 4, lineStyle: 0 },
  upper: { color: "#d64545", lineWidth: 2, lineStyle: 2 },
  lower: { color: "#2f9e44", lineWidth: 2, lineStyle: 2 },
} as const;

export interface Series {
  candles: Candle[];
  channelLines: Record<string, LinePoint[]>;
  zones: Record<string, Band>;
}

// lightweight-charts takes UNIX seconds. Feeding it nanoseconds puts every
// candle somewhere around the year 58,000, with no error and an empty chart.
//
// This is the narrowing REQ-WP-061 allows: the axis is seconds and the layout is
// floats, so nanoseconds cannot reach a pixel whatever this app does. The
// division happens in `bigint` (`chartSeconds`) so the *input* is exact -- what
// is given up is resolution the chart never had, not resolution the value had.
export function toSeconds(eventTimeNs: bigint): Time {
  return chartSeconds(eventTimeNs) as Time;
}

export function buildSeries({
  bars,
  channel,
}: {
  bars: BarOut[];
  channel: ChannelOut | null;
}): Series {
  const candles: Candle[] = bars
    .map((bar) => ({
      time: toSeconds(bar.close_time_ns),
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
    }))
    .sort((a, b) => (a.time as number) - (b.time as number));

  // An absent channel is not a flat one. Drawing a zero line would put a
  // boundary on the chart that no model ever produced, and a reader would have
  // no way to tell it from a real one.
  if (channel === null) {
    return { candles, channelLines: {}, zones: {} };
  }

  // The channel as the model fitted it: a log-linear band over its **lookback window**, ending at the bar
  // the snapshot was taken at (REQ-WP-082, PRD 13.2 and 27.5). `level(i) = level_now * exp(slope *
  // (i - last))` for the bars of the window -- exact, because the fit is least squares in log price and
  // its bounds are fixed residual offsets in log space. The first version repeated the *current* levels
  // for every bar of the history, so a channel fitted to the last fifteen hours was drawn as a flat
  // stripe across nine days it says nothing about.
  //
  // The window ends at `as_of_ns`, not at the last bar on the chart: a channel stored at an earlier
  // bar is drawn where it was (AS-SEEN-THEN), and no bar after it is used.
  const slope = channel.slope_log_per_bar;
  const window = Number.isFinite(slope)
    ? [...bars]
        .sort((a, b) => (a.close_time_ns < b.close_time_ns ? -1 : a.close_time_ns > b.close_time_ns ? 1 : 0))
        .filter((bar) => bar.close_time_ns <= channel.as_of_ns)
        .slice(-Math.max(0, Math.floor(channel.lookback)))
    : [];
  const along = (level: number): LinePoint[] =>
    window.map((bar, i) => ({
      time: toSeconds(bar.close_time_ns),
      value: level * Math.exp(slope * (i - (window.length - 1))),
    }));

  const width = channel.upper_now - channel.lower_now;
  const band = ([low, high]: readonly [number, number]): Band => ({
    from: channel.lower_now + width * low,
    to: channel.lower_now + width * high,
  });

  return {
    candles,
    // No usable slope, or no bar in the window: no lines. An absent channel is not a flat one.
    channelLines:
      window.length === 0
        ? {}
        : {
            center: along(channel.center_now),
            upper: along(channel.upper_now),
            lower: along(channel.lower_now),
          },
    zones: {
      upper: band(ZONES.upper),
      middle: band(ZONES.middle),
      lower: band(ZONES.lower),
    },
  };
}

export function markerFor(signal: SignalOut, _channel: ChannelOut | null): Marker {
  const short = signal.direction === "short";
  return {
    time: toSeconds(signal.opened_at_ns),
    // A short setup is a rejection from above, so its marker belongs above the
    // bar: the mark points at where the price was refused.
    position: short ? "aboveBar" : "belowBar",
    color: short ? "#d64545" : "#2f9e44",
    shape: short ? "arrowDown" : "arrowUp",
    text: `${signal.direction.toUpperCase()} · ${signal.boundary}`,
  };
}

// The window the chart opens on. REQ-US-002 asks for "exactly the signal's
// timestamp", and a view fitted to five hundred bars contains that instant
// while hiding it -- the reader is left to find the moment the alert was about.
//
// `null` means there is nothing to centre on, and the caller shows the whole
// history instead. Centring on a bar that does not exist would scroll the chart
// into empty space, which reads as a data outage rather than as an old link.
export function visibleRangeFor(
  bars: BarOut[],
  atNs: bigint | null,
  span: number,
): { from: number; to: number } | null {
  if (atNs === null || bars.length === 0) {
    return null;
  }
  const index = bars.findIndex((bar) => bar.open_time_ns <= atNs && atNs < bar.close_time_ns);
  if (index === -1) {
    return null;
  }
  const half = Math.floor(span / 2);
  // Clamped to the data at both ends: a range running past the last bar leaves
  // the signal off-centre with blank space beside it, which reads as missing
  // data rather than as the edge of the history.
  const from = Math.max(0, Math.min(index - half, bars.length - 1 - span));
  return { from: Math.max(0, from), to: Math.min(bars.length - 1, Math.max(0, from) + span) };
}

// Where the chart opens when no instant is named and a channel exists: the last two lookbacks of bars,
// so the channel fills the view. (Three was tried first and a screenshot showed it still took in a spike
// a day and a half earlier, which stretched the axis until the channel was a thin ribbon again.) Fitting the whole history (the first version) made a window of sixty bars
// a few pixels wide, and let a spike days earlier stretch the price axis until the channel was a hairline.
// The history stays reachable by scrolling. `null` for no bars: the chart fits its content as before.
export function visibleRangeForChannel(
  bars: BarOut[],
  lookback: number,
  margin = 5,
): { from: number; to: number } | null {
  if (bars.length === 0) {
    return null;
  }
  const last = bars.length - 1;
  return { from: Math.max(0, last - 2 * lookback), to: last + margin };
}

// --- where a chart opens, and whether it follows the newest bar (REQ-WP-108) ------------------------------------------------------------
//
// Compared with Investing's, the chart did not look live: the last bar was a few pixels wide under the volume profile, the visible range
// ended at the last *stored* bar so live bars beyond it were off the right edge, and the price axis spanned the whole history, so a move
// of ten dollars was a pixel. A chart opens on the newest bars, with room on the right, and follows the newest bar while the reader is
// looking at it.

/** How many bars a chart opens on: enough to read the trend, few enough that the newest bar is wide and the price axis is local. */
export const RECENT_BARS = 150;

/** The share of the plot kept clear on the right: the volume profile covers a quarter of it, and the newest bar must sit left of that. */
export const PROFILE_ROOM = 0.3;

/** The range a chart opens on: the newest `RECENT_BARS` and room on the right. `null` for no bars. */
export function recentRange(
  count: number,
  room: number,
  visible = RECENT_BARS,
): { from: number; to: number } | null {
  if (count === 0) {
    return null;
  }
  const span = Math.min(count, visible);
  const from = Math.max(0, count - visible);
  return { from, to: count - 1 + Math.ceil((span * room) / (1 - room)) };
}

/** Whether the reader is looking at the newest bar: the range reaches it. Scrolled back into history, it does not. */
export function followsLatest(range: { from: number; to: number } | null, lastIndex: number): boolean {
  return range !== null && range.to >= lastIndex - 0.5;
}

/** The range after `delta` bars arrived at the right: moved with them, so the newest bar stays where it was on screen. */
export function shiftedRange(range: { from: number; to: number }, delta: number): { from: number; to: number } {
  return { from: range.from + delta, to: range.to + delta };
}
