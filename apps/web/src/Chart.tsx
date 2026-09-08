// @trace: REQ-WP-009
//
// PRD section 27.2's overlays, for the four layers REQ-WP-009's acceptance
// names: candles, the channel's centre and boundaries, the setup zones, and a
// marker at the signal.
//
// The decision about *what* to draw lives in `series.ts`, where it can be
// tested; this attaches it to the library. jsdom cannot lay out a container,
// so a component test here would assert nothing about the picture -- which is
// why the split exists.

import { createChart, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { buildSeries, markerFor } from "./series";
import type { BarOut, ChannelOut, SignalOut } from "./types";

const ZONE_COLOURS: Record<string, string> = {
  upper: "rgba(214, 69, 69, 0.10)",
  middle: "rgba(120, 120, 120, 0.08)",
  lower: "rgba(47, 158, 68, 0.10)",
};

export function Chart({
  bars,
  channel,
  signal,
}: {
  bars: BarOut[];
  channel: ChannelOut | null;
  signal: SignalOut | null;
}): JSX.Element {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (container.current === null) {
      return;
    }
    const instance = createChart(container.current, {
      height: 480,
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    chart.current = instance;
    return () => {
      instance.remove();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    const instance = chart.current;
    if (instance === null) {
      return;
    }
    const { candles, channelLines, zones } = buildSeries({ bars, channel });

    const candlestick = instance.addCandlestickSeries();
    candlestick.setData(candles);
    if (signal !== null) {
      candlestick.setMarkers([markerFor(signal, channel)]);
    }

    for (const [name, points] of Object.entries(channelLines)) {
      const line = instance.addLineSeries({
        color: name === "center" ? "#4c6ef5" : "#868e96",
        lineWidth: name === "center" ? 2 : 1,
        lineStyle: name === "center" ? 0 : 2,
        priceLineVisible: false,
        title: name,
      });
      line.setData(points);
    }

    // Zones are drawn as price lines rather than filled areas: the library has
    // no band primitive, and faking one with two stacked areas would put a
    // shape on the chart whose edges do not mean what they look like.
    for (const [name, band] of Object.entries(zones)) {
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

    instance.timeScale().fitContent();
  }, [bars, channel, signal]);

  return <div ref={container} data-testid="chart" />;
}
