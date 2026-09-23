# Contract: the web modules

Three new modules and two changed ones, plus the behaviour `App` owns. The
frontend carries no timeframe table: every duration comes from the API response.

## `src/timeframes.ts` (new)

```ts
export const DEFAULT_TIMEFRAME = "15m";

export interface TimeframeOption {
  token: string;
  timeframeNs: number;
}

export function matchTimeframe(
  offered: readonly TimeframeOption[],
  token: string,
): TimeframeOption | null;
```

- `DEFAULT_TIMEFRAME` is the single spelling of the default; `deepLink.ts`
  imports it rather than repeating `"15m"`.
- `matchTimeframe` matches exactly, returning `null` for anything absent. No
  case folding, no trimming, no alias for `1H` or `60m` — a substituted
  timeframe under a token nobody configured is the silent fallback FR-006
  forbids.

## `src/deepLink.ts` (changed)

```ts
export function withTimeframe(search: string, token: string): string;
export function withMode(search: string, mode: ChannelMode): string;
```

Each returns a query string built from `search` with exactly one key written:

- `withTimeframe` sets `tf=<token>`; every other parameter is preserved
  byte-for-byte.
- `withMode` sets `as_seen_then=false` for `CURRENT REFIT` and **deletes** the
  key for `AS-SEEN-THEN` — absence is the default ADR-020 already reads.
- Repeated keys: the writers replace the first occurrence and drop the rest, so
  the result has one `tf`; `URLSearchParams.set`/`delete` already do this.
- The functions are pure string→string; the caller performs
  `history.replaceState(null, "", pathname + "?" + query)`.

`parseDeepLink` changes in one line: `params.get("tf") ?? DEFAULT_TIMEFRAME`.

## `src/api.ts` (changed)

```ts
export function fetchTimeframes(): Promise<Result<{ timeframes: { token: string; timeframe_ns: number }[] }>>;
```

`timeframe_ns` is a **number** (a duration), so `convertTimes` leaves it alone;
the returned options live in `timeframes.ts`'s `TimeframeOption` shape only
after the caller maps `timeframe_ns` → `timeframeNs`.

## `src/TimeframeControl.tsx` (new)

```ts
interface Props {
  offered: readonly TimeframeOption[];
  selected: string;
  onSelect: (token: string) => void;
}
```

- Renders one button per option, in the order given (the API sorts ascending).
- The in-force token's button carries `aria-pressed="true"` and is visibly
  distinct; a token in `selected` that is not offered renders no selected
  button, which is the refused state and is handled by `App` before this
  component is reached.
- Clicking calls `onSelect(token)`; the component holds no state and does not
  touch the address — the caller owns both.

## `src/App.tsx` (changed)

**Request gating.** No bars, channel, features or extrema request is issued
until the offered set has arrived. While it is in flight the page renders its
loading presentation.

**The in-force timeframe.** State initialised to `link.timeframe` (already
defaulted by the parser). All four requests take the matched option's
`timeframeNs`. The heading prints the in-force token.

**Refusal.** With the offered set loaded and `matchTimeframe` returning `null`,
the page renders exactly:

- a `role="alert"` element containing the in-force token and the offered tokens;
- no chart, and no series request of any kind.

**Offered-set failure.** `LoadState` reports `failed` with the client's error;
no chart.

**Address.** `onSelect` sets state and calls
`history.replaceState(null, "", link.path + "?" + withTimeframe(...))`; the mode
control's `onChange` does the same with `withMode`. The path is the one parsed
from the link, so unknown path segments survive. When the resulting query would
be empty, the `?` is omitted.

**Stale responses.** `load` carries a sequence number from a ref; a response
that is not the newest is discarded before any `setState`. Cleanup on unmount
does the same.

**Empty versus failed.** Unchanged from today: an empty series is `empty` and
the chart renders; a failed request is `failed` and it does not.
