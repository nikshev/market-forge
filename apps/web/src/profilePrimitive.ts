// @trace: REQ-WP-089
//
// The volume profile drawn at the right edge of the chart, on the chart's own price scale (PRD section 27.2): each price
// bin is a horizontal bar of unknown, sell and buy volume, the busiest at most a quarter of the plot wide. It is a
// series primitive, so it asks the series for every bin edge on every redraw and follows zoom and pan with the candles.
// What to draw is decided in `profileView.ts`; this only paints it.

import type { ISeriesPrimitive, SeriesAttachedParameter, Time } from "lightweight-charts";

import { MAX_PROFILE_FRACTION, profileGeometry } from "./profileView";
import type { VolumeProfileOut } from "./types";

export const BUY_COLOUR = "rgba(38, 166, 154, 0.8)";
export const SELL_COLOUR = "rgba(239, 83, 80, 0.8)";
export const UNKNOWN_COLOUR = "rgba(140, 140, 140, 0.6)";
const POC_OUTLINE = "#e8590c";

// Bars outside the value area are fainter, so the 70 % the volume concentrated in stands out.
const OUTSIDE_VALUE_AREA_ALPHA = 0.55;

// What the renderer uses of the library's canvas target: the part that does not need its types imported.
interface MediaScope {
  context: CanvasRenderingContext2D;
  mediaSize: { width: number; height: number };
}
interface MediaTarget {
  useMediaCoordinateSpace<T>(f: (scope: MediaScope) => T): T;
}

type Attached = SeriesAttachedParameter<Time>;

export class ProfilePrimitive implements ISeriesPrimitive<Time> {
  private param: Attached | null = null;

  constructor(private profile: VolumeProfileOut | null) {}

  attached(param: Attached): void {
    this.param = param;
  }

  detached(): void {
    this.param = null;
  }

  setProfile(profile: VolumeProfileOut | null): void {
    this.profile = profile;
    this.param?.requestUpdate();
  }

  paneViews(): [{ renderer: () => { draw: (target: never) => void } }] {
    return [{ renderer: () => ({ draw: (target) => this.draw(target as MediaTarget) }) }];
  }

  private draw(target: MediaTarget): void {
    const profile = this.profile;
    const param = this.param;
    if (profile === null || param === null) {
      return;
    }
    target.useMediaCoordinateSpace(({ context, mediaSize }) => {
      const rects = profileGeometry(profile, {
        plotWidth: mediaSize.width,
        plotHeight: mediaSize.height,
        maxFraction: MAX_PROFILE_FRACTION,
        priceToCoordinate: (price) => param.series.priceToCoordinate(price),
      });
      for (const rect of rects) {
        context.globalAlpha = rect.inValueArea ? 1 : OUTSIDE_VALUE_AREA_ALPHA;
        // One pixel off each bar's height so neighbouring bins read as separate rows.
        const height = Math.max(1, rect.height - 1);
        let x = rect.x;
        for (const [width, colour] of [
          [rect.unknownWidth, UNKNOWN_COLOUR],
          [rect.sellWidth, SELL_COLOUR],
          [rect.buyWidth, BUY_COLOUR],
        ] as const) {
          if (width > 0) {
            context.fillStyle = colour;
            context.fillRect(x, rect.y, width, height);
          }
          x += width;
        }
        if (rect.isPoc) {
          context.globalAlpha = 1;
          context.strokeStyle = POC_OUTLINE;
          context.lineWidth = 2;
          context.strokeRect(rect.x, rect.y, mediaSize.width - rect.x, height);
        }
      }
      context.globalAlpha = 1;
    });
  }
}
