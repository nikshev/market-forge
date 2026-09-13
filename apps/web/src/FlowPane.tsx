// @trace: REQ-WP-027
//
// PRD section 27.3's lower pane, attached to the page.
//
// This component decides nothing. Which points are drawn, which are gaps and
// what to say when there is nothing -- all of that is `panes.ts`, where it is
// tested. Here it is a selector, a line, and the three messages.

import { paneSeries, PANES } from "./panes";
import { chartMilliseconds } from "./time";
import type { FeaturePointOut } from "./types";

const WIDTH = 720;
const HEIGHT = 120;

export function FlowPane({
  points,
  feature,
  onSelect,
  failure = null,
}: {
  points: readonly FeaturePointOut[];
  feature: string;
  onSelect: (feature: string) => void;
  /** A load that failed. Never drawn as an empty pane -- REQ-WP-009's FR-016. */
  failure?: string | null;
}): JSX.Element {
  const series = paneSeries(points, feature);

  return (
    <section aria-label="Lower pane">
      <div role="group" aria-label="Pane">
        {PANES.map((pane) => (
          <button
            key={pane.feature}
            type="button"
            aria-pressed={pane.feature === feature}
            onClick={() => onSelect(pane.feature)}
          >
            {pane.label}
          </button>
        ))}
      </div>
      {failure === null ? null : (
        <p role="status" aria-label="Pane load">
          Could not load this pane: {failure}
        </p>
      )}
      {failure === null && series.state !== "ok" ? (
        <p role="status" aria-label="Pane contents">
          {series.note}
        </p>
      ) : null}
      {failure === null && series.state === "ok" ? (
        <svg
          width={WIDTH}
          height={HEIGHT}
          role="img"
          aria-label={`${feature} over ${series.points.length} point(s)`}
        >
          <polyline
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            points={plot(series.points, WIDTH, HEIGHT)}
          />
        </svg>
      ) : null}
    </section>
  );
}

function plot(
  points: readonly { at_ns: bigint; value: number }[],
  width: number,
  height: number,
): string {
  // Milliseconds, through the named narrowing: one pixel of this pane is minutes
  // wide, so nanosecond resolution cannot reach it. The division happens in
  // `bigint`, so what is given up is resolution the drawing never had.
  const times = points.map((p) => chartMilliseconds(p.at_ns));
  const values = points.map((p) => p.value);
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const [v0, v1] = [Math.min(...values), Math.max(...values)];
  // A flat series and a single point both give a zero span. Centring them is
  // the honest picture: the alternative divides by zero and draws nothing,
  // which would look exactly like the empty state this pane keeps separate.
  const spanT = t1 - t0 || 1;
  const spanV = v1 - v0 || 1;
  return points
    .map((p) => {
      const x = ((chartMilliseconds(p.at_ns) - t0) / spanT) * width;
      const y = height - ((p.value - v0) / spanV) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}
