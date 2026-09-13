// @trace: REQ-WP-028
//
// PRD section 27.2's markers for candidate versus confirmed extrema, and the
// rule PRD section 45's Phase 1A states about them:
//
//     no confirmed extremum can appear earlier than `known_at` in
//     `AS-SEEN-THEN` mode
//
// That is not a display preference. A turn happens at one instant and becomes
// knowable at a later one; a marker at the first, on a chart showing the past
// as it was seen then, claims the system knew about the turn before it did --
// the repaint section 13A.1 forbids, drawn where it will be believed.
//
// Two things have to be true together, and either alone looks like compliance:
// a turn is **hidden** until `known_at`, and once shown it sits at
// `extremum_time`. Drawing it at `known_at` never appears too early either, and
// is not where the turn was.

import { AS_SEEN_THEN } from "./types";
import type { ChannelMode, ConfirmedExtremumOut, ExtremumCandidateOut } from "./types";

export interface ExtremumMarker {
  at_ns: bigint;
  kind: "confirmed" | "candidate";
  type: string;
  price: string;
}

export function extremumMarkers({
  confirmed,
  candidates,
  mode,
  atNs,
}: {
  confirmed: readonly ConfirmedExtremumOut[];
  candidates: readonly ExtremumCandidateOut[];
  mode: ChannelMode;
  atNs: bigint;
}): ExtremumMarker[] {
  // In CURRENT REFIT the filter is deliberately absent. PRD section 27.5 makes
  // that mode the place where repaint-like differences are meant to be visible,
  // and filtering there would hide the very difference it exists to expose.
  const knowable = mode === AS_SEEN_THEN;

  const shown = confirmed.filter((e) => !knowable || e.known_at_ns <= atNs);

  // A candidate that became a shown confirmation is the same turn. Two markers
  // would say two turns happened.
  const superseded = new Set(
    shown.map((e) => e.source_candidate_id).filter((id): id is string => id !== null),
  );

  const marks: ExtremumMarker[] = [
    ...shown.map((e) => ({
      // Where the turn was, not when it was confirmed.
      at_ns: e.extremum_time_ns,
      kind: "confirmed" as const,
      type: e.extremum_type,
      price: e.price,
    })),
    ...candidates
      .filter((c) => (!knowable || c.observed_at_ns <= atNs) && !superseded.has(c.candidate_id))
      .map((c) => ({
        at_ns: c.candidate_time_ns,
        kind: "candidate" as const,
        type: c.candidate_type,
        price: c.price,
      })),
  ];

  return marks.sort((a, b) => (a.at_ns < b.at_ns ? -1 : a.at_ns > b.at_ns ? 1 : 0));
}
