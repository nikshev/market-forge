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

import { AS_SEEN_THEN, CURRENT_REFIT } from "./types";
import type { ChannelMode } from "./types";

export interface DeepLink {
  venue: string;
  symbol: string;
  timeframe: string;
  atNs: number | null;
  signalId: string | null;
  mode: ChannelMode;
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
    atNs: at === null ? null : Date.parse(at) * 1_000_000 || null,
    signalId: params.get("signal"),
    mode: modeFromQuery(params),
  };
}
