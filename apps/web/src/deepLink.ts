// @trace: REQ-WP-009
//
// PRD section 27.1's deep link, read back:
//   /chart/:venue/:symbol?tf=15m&at=<iso>&signal=<uuid>
//
// PRD section 27.5: "Default when opening signal deep-link: AS-SEEN-THEN."
// ADR-020 extends that to an unparseable value, because every alert this
// system has ever sent carries such a link -- a value mangled in transit must
// not silently become a refit, or old signals start looking better than they
// were and nothing says why.

import { overlaysFromQuery } from "./overlays";
import { nanosecondsFromIso } from "./time";
import type { OverlaySelection } from "./overlays";
import { AS_SEEN_THEN, CURRENT_REFIT } from "./types";
import type { ChannelMode } from "./types";

export interface DeepLink {
  venue: string;
  symbol: string;
  timeframe: string;
  atNs: bigint | null;
  signalId: string | null;
  mode: ChannelMode;
  // REQ-US-002: which of PRD section 27.2's layers were on when the alert
  // fired, and whether that could be read at all.
  overlays: OverlaySelection;
  // Which pool the `dex_liquidity_bands` layer draws (REQ-WP-059). Section 27.1
  // does not list these, and there is no other way to know: a CEX venue and
  // symbol do not name an AMM pool, and inferring one would be section 17's
  // cross-venue mapping done by guess. Both are null unless both are readable.
  chainId: number | null;
  pool: string | null;
}

// A chain id, or nothing. Nothing on anything that is not a positive integer:
// `Number("12abc")` is NaN and `parseInt` would return 12, which would request
// depth from a chain nobody named.
export function chainFromQuery(params: URLSearchParams): number | null {
  const raw = params.get("chain");
  if (raw === null || !/^[1-9][0-9]*$/.test(raw)) {
    return null;
  }
  return Number(raw);
}

export function modeFromQuery(params: URLSearchParams): ChannelMode {
  // Only the exact string "false" turns it off. Anything else -- missing,
  // empty, misspelled, truncated -- is the safe view.
  return params.get("as_seen_then") === "false" ? CURRENT_REFIT : AS_SEEN_THEN;
}

export function parseDeepLink(pathname: string, search: string): DeepLink | null {
  const match = /^\/chart\/([^/]+)\/([^/]+)\/?$/.exec(pathname);
  if (match === null) {
    return null;
  }
  const params = new URLSearchParams(search);
  const at = params.get("at");
  return {
    venue: decodeURIComponent(match[1]),
    symbol: decodeURIComponent(match[2]),
    timeframe: params.get("tf") ?? "15m",
    // `Date.parse` gives milliseconds and the multiplication is done in
    // `bigint`: `ms * 1e6` in floating point lands above the safe range and
    // rounds the instant the link was built to name (REQ-WP-061).
    atNs: at === null ? null : nanosecondsFromIso(at),
    signalId: params.get("signal"),
    mode: modeFromQuery(params),
    overlays: overlaysFromQuery(params),
    // Together or not at all. A pool with no chain is not addressable and a
    // chain with no pool asks for nothing, and either alone would produce a
    // request that could only fail.
    chainId: params.get("pool") === null ? null : chainFromQuery(params),
    pool: chainFromQuery(params) === null ? null : params.get("pool"),
  };
}
