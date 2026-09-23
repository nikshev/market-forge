# Phase 0 Research: The markets route

## How `App` learns which view to render

**Decision**: a mount-stable pathname, checked in a fixed order:

```text
"/" or "/markets"  -> Markets
parseDeepLink(...) -> Chart
otherwise          -> the existing placeholder
```

**Rationale**: `App` already froze its parsed link at mount
([[REQ-WP-074]]) because re-parsing per render caused a fetch loop. The route
decision is the same shape and must be equally stable, or a re-render during a
markets fetch could flip the view.

**Alternatives considered**: a routing library (rejected: two routes; ADR-021's
gates keep the bundle small and a dependency for two string comparisons is not
justified); `window.location` read inline in render (rejected: unstable
identity, the defect just fixed); a state variable updated by a popstate
listener (rejected: nothing navigates client-side — every move is a full page
load, so there is no event to listen for).

## What the view does with the offered set's failure

**Decision**: the rows still render; the timeframe area states the failure; row
links use `DEFAULT_TIMEFRAME`.

**Rationale**: the market list and the timeframe control are two independent
reads. Making one failure hide the other's data would overstate the blast
radius. The links still have to carry *some* `tf`; the documented default is
the only honest one, and it is already defined once in `timeframes.ts`.

**Alternatives considered**: disabling the links (rejected: a link at the
default is what the reader would get by typing the URL; disabling turns a
control failure into a data outage); hiding the rows (rejected above).

## How the destination is encoded

**Decision**: `marketHref(venue, symbol, token)`:
`/chart/${encodeURIComponent(venue)}/${encodeURIComponent(symbol)}?tf=${token}`,
with the token validated by construction (it comes from the offered set).

**Rationale**: venues and symbols are exchange identifiers — ASCII in practice,
but the API accepts any non-empty string and the deep link is decoded with
`decodeURIComponent`, so the encoder is the inverse of the parser that already
exists. A token with characters needing encoding would be a configured token
that `parse_list` accepted; `URLSearchParams` is not needed for one known-safe
key/value pair, and the exact byte string is easier to assert.

**Alternatives considered**: `new URLSearchParams({tf: token}).toString()`
(equivalent for these values, but it sorts and encodes differently in edge
cases, and SC-003 asserts bytes); building the URL from `window.location.origin`
(rejected: the bundle has no origin at test time and a relative href is
correct).

## Where `fetchMarkets` lives and what it returns

**Decision**: `api.ts` gains `fetchMarkets(): Promise<Result<{markets: MarketOut[]}>>`,
a `MarketOut` interface in `types.ts` mirroring the wire schema:
`venue`, `symbol`, `market_type`, `setup_score: number | null`,
`rank_score: number | null`, `confidence: number | null`.

**Rationale**: the existing client owns the `Result` convention and the `_ns`
conversion. The markets payload has no `_ns` fields, so `convertTimes` passes
it through untouched — a property worth a test precisely because it is a
non-event.

**Alternatives considered**: reading the response in the component (rejected:
duplicates the error convention); reusing the chart's `fetchBars`-style
signature (n/a).

## How the row order is kept

**Decision**: render `markets` in array order, with a test whose fixture's
alphabetical order differs from its API order.

**Rationale**: FR-001 and SC-001 are about an absence of sorting. A fixture
sorted by symbol as well as by rank would pass whichever way the code sorted —
the same trap [[REQ-WP-073]]'s tests were written to avoid.

## What the rows contain

**Decision**: symbol, venue, market type, and the three scores via
`scoreLabel`. No price, no sparkline, no change percentage.

**Rationale**: the spec's "current state is the list" rule. A price column
would need a per-market bars read — N requests — or a new aggregate, which the
requirement forbids. `scoreLabel` centralises the null rule.

## Testing strategy

- Pure helpers (`marketHref`, `scoreLabel`) get their own file: bytes and the
  null rule are easiest to assert without React.
- `Markets.test.tsx` stubs `fetch` and inspects rows, hrefs and states, the
  same harness style as `chartTimeframeControl.test.tsx`.
- `routing.test.tsx` renders `App` at three paths and asserts which view
  appears — including that an unknown path keeps the placeholder.
- A click-through test changes the timeframe and re-reads the row's `href`,
  proving the chosen `tf` reaches the destination without a browser navigation.
