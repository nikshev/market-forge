// @trace: REQ-WP-089
//
// What the volume profile at the side of the chart looks like, decided in pure functions so it can be tested without a
// canvas, and the words that say how much of its window it covers. The primitive only paints what this returns.

import type { VolumeProfileOut } from "./types";

const MINUTE_NS = 60_000_000_000;
const HOUR_NS = 60 * MINUTE_NS;
const DAY_NS = 24 * HOUR_NS;

/** The busiest bin is at most this share of the plot's width, so the profile never hides the candles. */
export const MAX_PROFILE_FRACTION = 0.25;

export interface ProfileRect {
  low: number;
  high: number;
  /** Left edge of the whole bar and its top, in the plot's pixels. */
  x: number;
  y: number;
  height: number;
  /** Left to right: unknown, then sell, then buy, ending at the plot's right edge. */
  unknownWidth: number;
  sellWidth: number;
  buyWidth: number;
  isPoc: boolean;
  inValueArea: boolean;
}

export interface PlotGeometry {
  plotWidth: number;
  plotHeight: number;
  maxFraction: number;
  /** The series' own price scale: `null` when the price is off the scale. */
  priceToCoordinate: (price: number) => number | null;
}

export function profileGeometry(profile: VolumeProfileOut, plot: PlotGeometry): ProfileRect[] {
  const parts = profile.bins.map((bin) => ({
    bin,
    buy: Number(bin.buy),
    sell: Number(bin.sell),
    unknown: Number(bin.unknown),
  }));
  const totals = parts.map((p) => p.buy + p.sell + p.unknown);
  const busiest = Math.max(0, ...totals);
  if (busiest <= 0) {
    return [];
  }
  const areaLow = Number(profile.value_area_low);
  const areaHigh = Number(profile.value_area_high);
  const scale = (plot.plotWidth * plot.maxFraction) / busiest;

  const rects: ProfileRect[] = [];
  parts.forEach((part, index) => {
    const total = totals[index]!;
    if (total <= 0) {
      return;
    }
    const low = Number(part.bin.low);
    const high = Number(part.bin.high);
    const a = plot.priceToCoordinate(low);
    const b = plot.priceToCoordinate(high);
    // A bin whose edge the scale cannot place is not drawn: guessing where it is would put volume at a price it was
    // not traded at.
    if (a === null || b === null) {
      return;
    }
    const top = Math.min(a, b);
    const bottom = Math.max(a, b);
    if (bottom < 0 || top > plot.plotHeight) {
      return;
    }
    const width = total * scale;
    rects.push({
      low,
      high,
      x: plot.plotWidth - width,
      y: top,
      height: bottom - top,
      unknownWidth: part.unknown * scale,
      sellWidth: part.sell * scale,
      buyWidth: part.buy * scale,
      isPoc: index === profile.poc_index,
      inValueArea: low >= areaLow && high <= areaHigh,
    });
  });
  return rects;
}

/** A duration in the largest two units that read well: "45 m", "3 h 20 m", "1 d 2 h". */
export function formatDuration(ns: number): string {
  const days = Math.floor(ns / DAY_NS);
  const hours = Math.floor((ns % DAY_NS) / HOUR_NS);
  const minutes = Math.floor((ns % HOUR_NS) / MINUTE_NS);
  const pieces: string[] = [];
  if (days > 0) {
    pieces.push(`${days} d`);
    if (hours > 0) {
      pieces.push(`${hours} h`);
    }
  } else if (hours > 0) {
    pieces.push(`${hours} h`);
    if (minutes > 0) {
      pieces.push(`${minutes} m`);
    }
  } else {
    pieces.push(`${minutes} m`);
  }
  return pieces.join(" ");
}

/** How much of its window the profile's data spans. Never the whole window unless it is. */
export function coverageLine(profile: VolumeProfileOut): string {
  const window = profile.window.replace(/^(\d+)([hd])$/, "$1 $2");
  return profile.complete
    ? `${window} window, complete`
    : `covers ${formatDuration(profile.covered_ns)} of ${window}`;
}
