// @trace: REQ-WP-009
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
  if (state === "empty") {
    return <p role="status">No bars in this range.</p>;
  }
  if (state === "disconnected") {
    return <p role="status">This chart is no longer live — updates have stopped.</p>;
  }
  return (
    <p role="alert">
      The data could not be loaded{detail ? `: ${detail}` : "."}
    </p>
  );
}
