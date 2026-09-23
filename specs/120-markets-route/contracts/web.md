# Contract: the markets view

Two new modules and one changed function. No backend interface changes: the
view consumes `GET /api/v1/markets` (already served) and
`GET /api/v1/timeframes` ([[REQ-WP-074]]).

## `src/types.ts` (changed)

```ts
export interface MarketOut {
  venue: string;
  symbol: string;
  market_type: string;
  setup_score: number | null;
  rank_score: number | null;
  confidence: number | null;
}
```

The existing home for wire shapes (`BarOut`, `ChannelOut`, …).

## `src/markets.ts` (new)

```ts
export function marketHref(venue: string, symbol: string, token: string): string;
export function scoreLabel(value: number | null): string;
```

- `marketHref` returns exactly
  `/chart/<encodeURIComponent(venue)>/<encodeURIComponent(symbol)>?tf=<token>`.
  No leading origin, no trailing slash, no reordering.
- `scoreLabel` returns `"unscored"` for `null` and `value.toFixed(2)`
  otherwise. It never treats `0` as absent.

## `src/api.ts` (changed)

```ts
export function fetchMarkets(): Promise<Result<{ markets: MarketOut[] }>>;
```

Requests `/api/v1/markets` with no parameters. Failures arrive as
`Result` values, like every other call.

## `src/Markets.tsx` (new)

```ts
export function Markets(): JSX.Element;
```

- Fetches the markets and the offered set on mount; no request depends on the
  other's answer.
- Renders a `TimeframeControl` when the offered set is available; its selected
  value is the view's chosen token (`DEFAULT_TIMEFRAME` initially).
- Renders one `<a>` per market whose `href` is `marketHref(venue, symbol, chosen)`.
  The link text includes the symbol; venue, market type and the three scores
  are visible in the row.
- Markets failure: a `role="alert"` with the detail, and **no rows**.
- Empty list: a `role="status"` saying there are no markets, and no alert.
- Offered-set failure: the failure stated where the control would be; rows
  still render, their links built with `DEFAULT_TIMEFRAME`.
- Does not sort. Does not aggregate. Does not fetch bars.

## `src/App.tsx` (changed)

- Holds the mount-time pathname (`useState` initializer, like the link).
- Route order: `/` or `/markets` → `<Markets />`; otherwise the existing
  chart/placeholder logic, unchanged. `/chart/...` behaves exactly as
  [[REQ-WP-074]] left it.

## `docs/deployment.md` (changed)

Names `/markets` (and `/`) where "Reach it" already names the chart, so the
document lists what a deployment serves.
