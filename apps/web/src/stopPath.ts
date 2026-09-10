// @trace: REQ-WP-032
//
// PRD section 44A.33 lists fifteen things a position view must display, and
// then states the rule the list cannot state for itself:
//
//     `AS-SEEN-THEN` mode must show the stop path exactly as generated
//     live/replay, not recompute a prettier historical trail.
//
// The list is a drawing. The line under it is the requirement, and it is the
// one a view breaks by doing the easy thing: given a position and a price
// series, recomputing the trail is less work than carrying the proposals,
// produces a smoother line, and draws each stop from anchors confirmed after
// the instant it draws them at -- a chart of a stop that could not have been
// placed. That is Principle I's look-ahead wearing the appearance of polish.
//
// This module takes no bars. The rule is a promise about intent until the
// input a recomputation needs is gone, at which point it is a property of a
// signature, and reintroducing it is a parameter appearing in a diff.

import { AS_SEEN_THEN } from "./types";
import type {
  ChannelMode,
  ExcursionOut,
  PositionOut,
  StopAnchorOut,
  StopProposalOut,
} from "./types";

export type StopLevelLabel = "entry" | "initial" | "hard" | "current";

export interface StopLevel {
  label: StopLevelLabel;
  price: string;
}

export interface StopPathPoint {
  at_ns: number;
  price: string;
  kind: "moved" | "held" | "refused";
  reasons: string[];
  anchor: StopAnchorOut | null;
}

export interface StopPathView {
  state: "ok" | "empty" | "inconsistent";
  note: string;
  levels: StopLevel[];
  path: StopPathPoint[];
  openRiskR: number | null;
  lockedProfitR: number;
  mfeR: number | null;
  maeR: number | null;
}

function levelsOf(position: PositionOut): StopLevel[] {
  const levels: StopLevel[] = [
    { label: "entry", price: position.average_entry_price },
    { label: "initial", price: position.initial_stop_price },
  ];
  // An absent hard stop is absent. Substituting the initial stop would draw one
  // line where the position has two and claim there is less room below than
  // there is.
  if (position.hard_stop_price !== null) {
    levels.push({ label: "hard", price: position.hard_stop_price });
  }
  levels.push({ label: "current", price: position.current_strategy_stop });
  return levels;
}

function pointOf(proposal: StopProposalOut): StopPathPoint {
  return {
    at_ns: proposal.at_ns,
    price: proposal.price,
    kind: proposal.refused ? "refused" : proposal.moved ? "moved" : "held",
    // Verbatim, including a code this build has never heard of. A dropped
    // reason is a newly added veto that reads as no veto at all.
    reasons: [...proposal.reasons],
    anchor: proposal.anchor,
  };
}

export function stopPath({
  position,
  proposals,
  excursion,
  mode,
  atNs,
}: {
  position: PositionOut;
  proposals: readonly StopProposalOut[];
  excursion: ExcursionOut;
  mode: ChannelMode;
  atNs: number;
}): StopPathView {
  const levels = levelsOf(position);

  const entry = Number(position.average_entry_price);
  const initial = Number(position.initial_stop_price);
  const current = Number(position.current_strategy_stop);
  const side = position.side === "LONG" ? 1 : -1;
  // Section 44A.24's `R0`, from the position's own accepted risk. Knowable
  // whether or not the policy ever ran, which is why an empty path does not
  // make risk unknown.
  const r0 = side * (entry - initial);
  const openRiskR = r0 > 0 ? Math.max(0, (side * (entry - current)) / r0) : null;
  const lockedProfitR = r0 > 0 ? Math.max(0, (side * (current - entry)) / r0) : 0;

  // In CURRENT REFIT the filter is deliberately absent, for the reason
  // `extrema.ts` gives: section 27.5 makes that mode the place repaint-like
  // differences are meant to be visible.
  const knowable = mode === AS_SEEN_THEN;
  const shown = proposals.filter((p) => !knowable || p.at_ns <= atNs);

  // An anchor confirmed after the decision that used it is the look-ahead this
  // whole requirement exists to prevent, arriving as data rather than as code.
  // Dropping the anchor would render a clean chart from a wrong path; drawing
  // it renders the forbidden chart. Neither leaves a reader anywhere to notice.
  const impossible = shown.find((p) => p.anchor !== null && p.anchor.known_at_ns > p.at_ns);
  if (impossible !== undefined) {
    return {
      state: "inconsistent",
      note:
        `the proposal at ${impossible.at_ns} cites an anchor that became knowable ` +
        `at ${impossible.anchor?.known_at_ns}, after the decision was made`,
      levels,
      path: [],
      openRiskR,
      lockedProfitR,
      mfeR: excursion.mfe_r,
      maeR: excursion.mae_r,
    };
  }

  const path = [...shown].sort((a, b) => a.at_ns - b.at_ns).map(pointOf);

  return {
    state: path.length === 0 ? "empty" : "ok",
    note:
      path.length === 0
        ? "no path: no stop decision was recorded for this position at this instant"
        : `${path.length} recorded stop decisions`,
    levels,
    path,
    openRiskR,
    lockedProfitR,
    // Null, never zero. An excursion over nothing observed is not a flat one.
    mfeR: excursion.mfe_r,
    maeR: excursion.mae_r,
  };
}
