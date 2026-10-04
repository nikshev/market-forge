// @trace: REQ-WP-009
// @trace: REQ-WP-083
//
// FR-015. Three situations put an empty chart on screen and mean entirely
// different things:
//
//   empty         the range holds no bars — a fact about the market
//   failed        the request did not succeed — a fact about us
//   disconnected  updates have stopped — the chart is history, not live
//
// Leaving them indistinguishable is the same failure PRD section 25.6 forbids
// for alerts: a stale view that looks current is worse than an obviously
// broken one, because it will be acted on.

import Alert from "@mui/material/Alert";

export type LoadStateKind = "ok" | "empty" | "failed" | "disconnected";

export function LoadState({
  state,
  detail,
}: {
  state: LoadStateKind;
  detail?: string;
}): JSX.Element | null {
  if (state === "ok") {
    return null;
  }
  // Alerts that keep the roles the paragraphs had: `status` for a fact about the market or the feed, `alert`
  // for a fact about us. Material's Alert defaults to `alert` for all of them, so the status ones say so.
  if (state === "empty") {
    return (
      <Alert severity="info" role="status" sx={{ my: 1 }}>
        No bars in this range.
      </Alert>
    );
  }
  if (state === "disconnected") {
    return (
      <Alert severity="warning" role="status" sx={{ my: 1 }}>
        This chart is no longer live — updates have stopped.
      </Alert>
    );
  }
  return (
    <Alert severity="error" role="alert" sx={{ my: 1 }}>
      The data could not be loaded{detail ? `: ${detail}` : "."}
    </Alert>
  );
}
