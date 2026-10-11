---
id: REQ-WP-096
title: "The venue-basis pane has a consensus: the venues' quotes become a consensus mid at every minute close"
type: work-package
prd_ref: "§17.1, §17.3, §27.3; owner's direction 2026-10-11"
prd_lines: "2520-2552, 4423-4436"
phase: null
status: planned
depends_on: [REQ-WP-095, REQ-WP-091]
tags: [consensus, venue-basis, quotes, panes]
hard_gated: false
---

## Requirement

[[REQ-WP-091]] built the consensus line and the venue-basis pane and left them reading "no data" "until the book
subscription exists". The API already merges `venue_basis_bps` from two tables, `quotes` and `consensus`; the
library `crossvenue/consensus.py` computes the median; **nothing writes either table**. [[REQ-WP-095]] writes
`quotes`. This requirement writes `consensus`.

1. **A pass in the worker writes one `consensus` row per (asset, market type) at every minute close**, from the
   `quotes` of the venues of that market type at or before the close, through the existing `consensus_mid`
   (median of fresh mids, a stale or late quote excluded with a reason, fewer than two venues refused). Every
   timeframe's bar close is also a minute close, so one cadence serves every timeframe the chart can show.
2. **A refusal is stored, not skipped**: the row exists with its `refusal_reason` and no price, because the line's
   absence has to be explainable ([[REQ-WP-091]]).
3. **The asset of a venue's symbol comes from the registry** (`crossvenue/consensus.py`'s `AssetRegistry`), the
   same one the API uses, so the writer and the reader cannot disagree about which venues are one asset.

What the deployment's own venues allow, stated rather than discovered later: Bybit and OKX are both perpetuals of
the same pair, so **BTC has a perpetual consensus of two venues, and the pane works for those two series**.
Binance's series are spot markets, and no other spot venue is ingested, so **a spot consensus has one venue and
is refused**: the Binance panes say so. Making them live needs a second spot venue; adding one (for example OKX
`BTC-USDT` spot, trades only, the same ingest image) is an option this requirement records and does not decide.

## Acceptance

- For a fixture of quotes from two and from three venues the stored consensus equals the median; a stale quote
  and a later quote are excluded with a reason; one venue stores a refusal row with a reason and no price.
- The consensus at a minute close is unchanged when quotes after it are appended (a test).
- The pass is idempotent: running it over the same range twice stores each close once.
- On the running stack, `GET` of the venue-basis read for Bybit and OKX BTC returns points whose value equals
  `10000 * (mid_i / consensus_mid - 1)` for the stored mids, and the Binance read returns the refusal reason
  instead of a number. The recorded query shows both.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-148-consensus-producer]]
- **Outcomes:** [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

`venue_basis_bps` stays a read-time merge in the API ([[REQ-WP-091]]'s design). It is not duplicated into
`feature_snapshots`, so there is one place to correct it.
