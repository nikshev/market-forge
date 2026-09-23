# Phase 1 Data Model: The markets route

No table, no schema, no new endpoint. What follows is the wire shape the view
consumes and the view's own state.

## `MarketOut` — the wire row (already served by §28.1)

| field | type | meaning |
|---|---|---|
| `venue` | `str` | the venue identifier, as configured |
| `symbol` | `str` | the instrument, as configured |
| `market_type` | `str` | `spot`, `perp`, … |
| `setup_score` | `float \| null` | §22.1's score for the market's latest setup |
| `rank_score` | `float \| null` | §43's ranking input; null when unscored |
| `confidence` | `float \| null` | the share of §22.1's 100 points any family could speak to |

**Nullability is a claim, not a gap.** The API's own docstring: a zero "would
say the setup was examined and found worthless, which is a different claim from
'not examined' — and the list is sorted on it." The view must preserve that
distinction (FR-002).

**Order.** The API returns markets ranked by §43 with unscored ones last. The
view renders the array as received; it never sorts.

## `marketHref(venue, symbol, token)` — the destination

```text
/chart/<encodeURIComponent(venue)>/<encodeURIComponent(symbol)>?tf=<token>
```

- The path segments are the inverse of `parseDeepLink`'s
  `decodeURIComponent`.
- The token comes from the offered set; the only tokens that reach this
  function are ones `parse_list` accepted.
- SC-003 asserts the string byte for byte against a pasted-link equivalent.

## `scoreLabel(value)` — the display rule, in one place

| input | output |
|---|---|
| `null` | `"unscored"` |
| `0.0` | `"0.00"` |
| `0.834` | `"0.83"` |

Two decimals, matching how the chart and the explanations already render
scores. A zero is a real score and renders as one — the rule is about `null`,
not about falsiness.

## The view's state

| value | type | meaning |
|---|---|---|
| `markets` | `MarketOut[] \| null` | `null` until the read arrives |
| `marketsFailure` | `string \| null` | the client's error, when the read failed |
| `offered` | `TimeframeOption[] \| null` | from `GET /api/v1/timeframes` |
| `offeredFailure` | `string \| null` | its error, when it failed |
| `timeframe` | `string` | the chosen token; `DEFAULT_TIMEFRAME` initially |
| `path` | `string` | the mount-time pathname, deciding the view |

## States the view can be in

| state | markets | offered | renders |
|---|---|---|---|
| loading | `null` | any | the loading presentation (nothing but the heading) |
| failed | failure | any | `role="alert"` with the detail; **no rows** |
| empty | `[]` | any | `role="status"`: there are no markets — not a failure |
| ok | rows | set | the rows, links carrying `timeframe` |
| ok, control failed | rows | failure | the rows with default-timeframe links, and the control's failure stated |

## Relationships

```text
GET /api/v1/markets ──> MarketOut[] ──> one row each ──> scoreLabel per score
GET /api/v1/timeframes ──> TimeframeOption[] ──> TimeframeControl ──> chosen token
                                                            │
                              marketHref(venue, symbol, chosen) ──> <a href>
                                                            │
                                    /chart/:venue/:symbol?tf=<chosen>
```
