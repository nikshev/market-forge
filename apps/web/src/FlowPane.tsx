// @trace: REQ-WP-083
// @trace: REQ-WP-027
// @trace: REQ-WP-084
//
// PRD section 27.3's lower pane, attached to the page.
//
// This component decides nothing. Which points are drawn, which are gaps and
// what to say when there is nothing -- all of that is `panes.ts`, where it is
// tested. Here it is a selector, a line, and the three messages.

import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
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
  available,
}: {
  points: readonly FeaturePointOut[];
  /** The selected pane, or `null` when none has data (REQ-WP-084). */
  feature: string | null;
  onSelect: (feature: string) => void;
  /**
   * The panes that have data in this view. A pane outside the set says "no data" and cannot be pressed.
   * `null` means not known -- loading, or the load failed -- and says nothing of any pane; absent is the
   * same, so a caller that does not know keeps the old behaviour exactly.
   */
  available?: ReadonlySet<string> | null;
  /** A load that failed. Never drawn as an empty pane -- REQ-WP-009's FR-016. */
  failure?: string | null;
}): JSX.Element {
  const series = paneSeries(points, feature ?? "");
  const known = available !== undefined && available !== null;

  return (
    <Box component="section" aria-label="Lower pane" sx={{ mt: 2 }}>
      <Box sx={{ overflowX: "auto", pb: 0.5 }}>
        <ToggleButtonGroup
          exclusive
          size="small"
          color="primary"
          aria-label="Pane"
          value={feature}
          onChange={(_, next: string | null) => {
            if (next !== null) {
              onSelect(next);
            }
          }}
        >
          {PANES.map((pane) => {
            // Disabled, not hidden: the row keeps its shape as data arrives, and the reader learns what
            // exists. The name stays the visible text ("CVD no data"), so a pane with data is the button it was.
            const empty = known && !available.has(pane.feature);
            return (
              <ToggleButton key={pane.feature} value={pane.feature} disabled={empty}>
                {pane.label}
                {empty ? (
                  <Typography component="span" variant="caption" sx={{ ml: 0.75, fontWeight: 400 }}>
                    no data
                  </Typography>
                ) : null}
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>
      </Box>
      {failure === null ? null : (
        <Typography role="status" aria-label="Pane load" color="error" sx={{ mt: 1 }}>
          Could not load this pane: {failure}
        </Typography>
      )}
      {failure === null && feature === null && known && available.size === 0 ? (
        <Typography role="status" aria-label="Pane contents" color="text.secondary" sx={{ mt: 1 }}>
          No pane has data for this view
        </Typography>
      ) : null}
      {failure === null && feature !== null && series.state !== "ok" ? (
        <Typography role="status" aria-label="Pane contents" color="text.secondary" sx={{ mt: 1 }}>
          {series.note}
        </Typography>
      ) : null}
      {failure === null && feature !== null && series.state === "ok" ? (
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
    </Box>
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
