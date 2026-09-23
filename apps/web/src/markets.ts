// @trace: REQ-WP-075
//
// The two rules of the markets view that are easiest to get subtly wrong, as
// pure functions so they can be asserted without a renderer: the bytes of the
// destination link, and what "unscored" means.
//
// No token table and no list of markets lives here. The view renders what the
// API returned and offers what `/api/v1/timeframes` reported.

/**
 * The deep link for a market at `token` — byte for byte
 * `/chart/:venue/:symbol?tf=<token>`, PRD §27.1's own shape.
 *
 * `encodeURIComponent` is the inverse of `parseDeepLink`'s
 * `decodeURIComponent`: a venue or symbol the API accepted as a non-empty
 * string must survive the trip, and the parser that reads it back is the
 * authority the encoding is checked against.
 */
export function marketHref(venue: string, symbol: string, token: string): string {
  return `/chart/${encodeURIComponent(venue)}/${encodeURIComponent(symbol)}?tf=${token}`;
}

/**
 * A score as a reader sees it.
 *
 * `null` is **unscored**, never `0.00`. The API sends null for a market nobody
 * has scored and ranks it last on purpose; rendering the absence as zero would
 * say the market was examined and found worthless, which is §28.1's own
 * distinction and the reason `MarketOut`'s scores are nullable.
 */
export function scoreLabel(value: number | null): string {
  return value === null ? "unscored" : value.toFixed(2);
}
