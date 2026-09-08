// @trace: REQ-WP-009
//
// What the chart draws, decided here rather than inside a component.
//
// `lightweight-charts` needs a laid-out container to render, which jsdom does
// not provide -- so a component test can never see a candle. Extracting the
// decision means the part that can be wrong is the part that is tested: which
// candles, which lines, which bands, and where the marker sits.

import type { Time } from "lightweight-charts";

import { ZONES } from "./types";
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

export interface Series {
  candles: Candle[];
  channelLines: Record<string, LinePoint[]>;
  zones: Record<string, Band>;
}

// lightweight-charts takes UNIX seconds. Feeding it nanoseconds puts every
// candle somewhere around the year 58,000, with no error and an empty chart.
export function toSeconds(eventTimeNs: number): Time {
  return Math.floor(eventTimeNs / 1e9) as Time;
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

  const at = (value: number): LinePoint[] =>
    candles.map((candle) => ({ time: candle.time, value }));

  const width = channel.upper_now - channel.lower_now;
  const band = ([low, high]: readonly [number, number]): Band => ({
    from: channel.lower_now + width * low,
    to: channel.lower_now + width * high,
  });

  return {
    candles,
    channelLines: {
      center: at(channel.center_now),
      upper: at(channel.upper_now),
      lower: at(channel.lower_now),
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
