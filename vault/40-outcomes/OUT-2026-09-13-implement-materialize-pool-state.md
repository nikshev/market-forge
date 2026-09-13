---
id: OUT-2026-09-13-implement-materialize-pool-state
step: implement
records: [REQ-WP-062]
commit: null
---

## What was done

`pipeline/pool_state.py`, and `transaction_index` on both DeFi event tables. 12
tests, **16 of 16 mutants caught**. `dex_state` has a producer.

## The canonical order was not expressible

§18.7 forbids sorting on timestamp and names `(block_number, transaction_index,
log_index)`. `dex_swaps` and `dex_liquidity` stored `block_number`, `tx_hash` and
`log_index` — **not the middle field**, though `ChainMeta` has carried it since
[[REQ-WP-014]] and every producer has it. A canonical table that cannot express
the canonical order is a gap, and the materialiser would otherwise have had to
fabricate the field.

Measured before changing anything, over 1,392 real logs in 803 blocks, 305 of
which hold more than one transaction against the pool: no duplicate
`(block, log_index)`, ordering by the triple identical to ordering by the pair,
and `tx_index` monotone in `log_index` in every block. **That is what made the
change safe, not what made it unnecessary** — EVM log indices are block-scoped
by convention, and the schema never said so.

Only a case the chain cannot produce distinguishes the two orderings, so the test
that proves the triple is used is explicitly synthetic and says why.

## A row states the same fact twice

`dex_liquidity` carries a signed `liquidity_delta` and an `event_type`. A `burn`
over a positive delta is a row that contradicts itself, and the tick map is built
from the sign — so resolving it either way produces a map that is plausible and
not the pool's. It is refused, naming both halves.

`modify` is §18.8's v4 `ModifyLiquidity`, which has no counterpart in
[[REQ-WP-015]]'s `PoolEventKind`. Its effect on the tick map is exactly its
signed delta, so it maps by sign — stated in the code rather than left for a
reader to infer from an enum that does not mention it.

## The sweep found a zero I had treated as an edge case

One mutant survived: `delta >= 0` against `delta > 0`, the mapping of a
zero-amount liquidity change. It looked equivalent — a change of zero adds zero
either way.

It is not equivalent, and the data says why. **Four of the fifteen mint/burn logs
in the fixture are burns of zero** — over a quarter — because that is how a
position is poked to settle fees before a collect. Applied as a burn,
[[REQ-WP-015]]'s guard refuses any sequence whose range has gone negative, which
is exactly what a partial replay looks like when the matching mint is older than
the window. So a row that moved nothing would have refused the whole replay, for
a fact about the window, reported against that row.

The branch is now explicit with the count behind it, and the test asserts the
count too, so a re-recorded fixture that no longer contains one is noticed rather
than quietly weakening the case.

## Two things the materialiser refuses

**An empty range.** A `dex_state` row saying a pool has no liquidity is a claim
about the pool; an empty query result is a fact about the query.

**A window with no swap.** `sqrt_price_x96` stays zero, which reads as a price of
zero rather than as an absence, and `active_liquidity` stays zero, which makes
[[REQ-WP-060]]'s tick-map invariant compare two numbers that mean nothing. A swap
is what anchors a reconstruction to the chain.

## What this does not deliver

A recent window is honestly `PARTIAL_TICKS`, and it is written rather than
skipped — refusing to write it would leave the table as empty as it was. Getting
`ANCHORED` rows needs replay from a pool's first initialised block or a
checkpoint read, which is ingestion work.

No feature computes an `active_liquidity` series from these rows, so §27.3's
`DEX active liquidity` pane stays unbuilt and stays on Phase 4's list.
