// @trace: REQ-WP-074
//
// What the deployment can serve, as the API reported it. This module carries no
// table of its own: [[REQ-WP-073]]'s FR-002 forbids a second list of timeframes
// in any component, and a token→duration map here would be exactly that. The
// durations arrive with the tokens.

/**
 * The token a link with no `tf` opens at.
 *
 * Written once. The parser defaults to it and nothing else repeats it, so there
 * is one answer to "which timeframe does an alert's bare link open at".
 */
export const DEFAULT_TIMEFRAME = "15m";

/** One timeframe the deployment produced, with the duration §28.2 takes. */
export interface TimeframeOption {
  token: string;
  timeframeNs: number;
}

/**
 * The offered option whose token equals `token`, or `null`.
 *
 * Exact match, deliberately. `1H`, `15m ` and `60m` are each a different token
 * from the deployment's, and accepting any of them would request one timeframe
 * under another's name — the silent substitution FR-006 forbids.
 */
export function matchTimeframe(
  offered: readonly TimeframeOption[],
  token: string,
): TimeframeOption | null {
  return offered.find((option) => option.token === token) ?? null;
}
