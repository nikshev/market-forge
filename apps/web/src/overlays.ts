// @trace: REQ-US-002
//
// Reading PRD section 27.2's layer list back out of the deep link.
//
// ADR-020 settled what to do with a mangled channel mode: fall back to the safe
// view, because "a value mangled in transit must not silently become a refit".
// The same reasoning applies here and produces a stricter rule, because an
// overlay list can be *partly* readable. A restored subset looks restored while
// missing whichever layer the reader most needed, and nothing on screen says
// which one went -- so a list containing anything unrecognised is discarded
// whole, and the page says the state could not be restored.

import { DEFAULT_OVERLAYS, OVERLAYS } from "./types";
import type { Overlay } from "./types";

export const RESTORED = "restored";
export const NOT_RECORDED = "not-recorded";
export const UNREADABLE = "unreadable";
export type RestorationState = typeof RESTORED | typeof NOT_RECORDED | typeof UNREADABLE;

export interface OverlaySelection {
  overlays: Overlay[];
  state: RestorationState;
}

export const RESTORATION_NOTICE: Record<RestorationState, string | null> = {
  [RESTORED]: null,
  [NOT_RECORDED]: "this alert did not record which layers were on — showing the defaults",
  [UNREADABLE]: "the link's layer list could not be read — showing the defaults",
};

export function overlaysFromQuery(params: URLSearchParams): OverlaySelection {
  const raw = params.get("overlays");
  if (raw === null) {
    return { overlays: [...DEFAULT_OVERLAYS], state: NOT_RECORDED };
  }
  // An empty parameter is a statement — "no layers were on" — not an absence.
  // Falling back to the defaults here would overrule it with a guess.
  const names = raw.split(",").filter((name) => name !== "");
  const known = new Set<string>(OVERLAYS);
  if (names.some((name) => !known.has(name))) {
    return { overlays: [...DEFAULT_OVERLAYS], state: UNREADABLE };
  }
  // Deduplicated in the PRD's own order, so the same set always reads the same
  // way. A repeat is sloppy rather than corrupt, and discarding the link over
  // one would lose a state that was perfectly readable.
  const chosen = new Set(names);
  return { overlays: OVERLAYS.filter((name) => chosen.has(name)), state: RESTORED };
}
