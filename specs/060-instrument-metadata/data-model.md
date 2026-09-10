# Phase 1 — Data model

## `Instrument`

| Field | Type | Rule |
|---|---|---|
| `venue`, `symbol`, `market_type` | `str` | non-empty |
| `base_asset`, `quote_asset`, `status` | `str` | non-empty |
| `tick_size`, `step_size`, `min_notional` | `Decimal` | positive; a float is refused, not converted |
| `contract_size` | `Decimal \| None` | positive when present; absent for an instrument with no contracts |

`contract_size` is absent rather than `1` for a spot instrument. A `1` would let
a later calculation multiply by it and be right by accident, which survives
review in a way that being wrong does not.

## `markets` table

Gains `base_asset`, `quote_asset`, `tick_size`, `step_size`, `min_notional`,
`contract_size`, `status`. The three sizes are `decimal` columns; `contract_size`
is a string so that absent (`""`) and a value are distinguishable on a plane
with no null.

Widening the schema changes its fingerprint. No dataset reference cites this
table today, so nothing is invalidated — true now rather than by design.

## `Market`

Gains `instrument: Instrument | None`, defaulted to `None` so every existing
construction site still compiles and every endpoint field is unchanged.
