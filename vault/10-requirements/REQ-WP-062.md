---
id: REQ-WP-062
title: A pool state is rebuilt from the rows the plane already holds
type: work-package
prd_ref: "§18.7, §18.12.2, §18.25"
prd_lines: "2841-2894, 3177-3193, 3568-3590"
phase: 4
status: implemented
depends_on: [REQ-WP-060, REQ-WP-053, REQ-PIPE-001]
tags: []
---

## Requirement

[[REQ-WP-053]] stores swaps and liquidity changes on the canonical plane.
[[REQ-WP-060]] rebuilds a pool state from events and gives it §18.12.2's
`reconstruction_quality`, and it is invoked with events a caller supplies. **No
path joins the two**: nothing reads the stored rows, replays them and writes a
`dex_state` row, so the table [[REQ-WP-060]] built is empty and §27.3's
`DEX active liquidity` pane has nothing to draw.

This is the same shape [[REQ-PIPE-001]] closed for the other seven tables, and it
is closed the same way: a replay over recorded input, not a daemon.

### The canonical order is not expressible from the stored rows

§18.7 states it plainly:

    Do not reconstruct state by sorting only on timestamp. Canonical event
    ordering is:

        block_number
        transaction_index
        log_index

`dex_swaps` and `dex_liquidity` store `block_number`, `tx_hash` and `log_index`.
**Neither stores `transaction_index`**, though `ChainMeta` carries it and every
producer has it. A canonical table that cannot express the canonical order is a
gap, and the materialiser would otherwise have to fabricate the field or lean on
a property of EVM log numbering that the schema never states.

Measured over 1,392 real logs of Ethereum's deepest USDC/WETH pool across 803
blocks, 305 of which hold more than one transaction touching the pool:

    duplicate (block_number, log_index)                        0
    ordering by (block, tx_index, log) == by (block, log)      True
    blocks where tx_index is not monotone in log_index         0

So adding the column changes no existing ordering — which is what makes the
change safe rather than what makes it unnecessary.

### A row states the same fact twice

`dex_liquidity` carries a signed `liquidity_delta` **and** an `event_type` of
`mint`, `burn`, `collect` or `modify`. A burn with a positive delta, or a mint
with a negative one, is a row that contradicts itself. It has to be refused:
picking either half would produce a tick map that is plausible and not the
pool's, and the sign is what the map is built from.

`modify` is §18.8's v4 `ModifyLiquidity` and has no counterpart in
[[REQ-WP-015]]'s `PoolEventKind`. Its effect on the tick map is exactly its
signed delta, so it maps by sign, and that mapping is stated rather than
inferred.

### Quality is measured from the result, not claimed by the caller

The materialiser derives [[REQ-WP-060]]'s quality from the state it built, and
the caller supplies only what cannot be measured: the replayed range and whether
it was contiguous. A pool replayed over a recent window yields `PARTIAL_TICKS`
and is written as such — that is the honest row, and refusing to write it would
leave the table as empty as it is now.

## Acceptance

- A materialiser reads `dex_swaps` and `dex_liquidity` for one pool and a block
  range, replays them in §18.7's order and writes one `dex_state` row.
- Both tables carry `transaction_index`, and the replay orders on it.
- The replay of the same rows twice produces the same state and the same row.
- A liquidity row whose `event_type` contradicts the sign of its
  `liquidity_delta` is refused, naming both.
- A `collect` row moves no liquidity and is still applied in order.
- A `modify` row is applied by the sign of its delta.
- The written row's `reconstruction_quality` is derived from the rebuilt state,
  and a partial window is written as `PARTIAL_TICKS` rather than skipped.
- A pool with no rows in the range writes nothing, and says so, rather than
  writing an empty state.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-103-materialize-pool-state]]
- **Tests:**
    - `tests/unit/pipeline/test_pool_state.py::test_a_collect_moves_no_liquidity_and_keeps_its_place`
    - `tests/unit/pipeline/test_pool_state.py::test_a_modify_row_is_applied_by_its_sign`
    - `tests/unit/pipeline/test_pool_state.py::test_a_range_with_no_rows_writes_nothing_and_says_so`
    - `tests/unit/pipeline/test_pool_state.py::test_a_replay_with_no_swap_has_no_price_and_is_refused`
    - `tests/unit/pipeline/test_pool_state.py::test_a_row_that_contradicts_itself_is_refused`
    - `tests/unit/pipeline/test_pool_state.py::test_a_zero_amount_burn_does_not_refuse_a_partial_replay`
    - `tests/unit/pipeline/test_pool_state.py::test_arrival_order_does_not_change_the_answer`
    - `tests/unit/pipeline/test_pool_state.py::test_both_tables_store_the_transaction_index`
    - `tests/unit/pipeline/test_pool_state.py::test_stored_rows_rebuild_the_pool_the_contract_reports`
    - `tests/unit/pipeline/test_pool_state.py::test_the_row_records_the_quality_the_state_earned`
    - `tests/unit/pipeline/test_pool_state.py::test_the_same_rows_twice_give_the_same_row`
    - `tests/unit/pipeline/test_pool_state.py::test_the_transaction_index_decides_before_the_log_index`
- **Code:**
    - `src/channelflow/pipeline/pool_state.py`
- **Outcomes:** [[OUT-2026-09-13-implement-materialize-pool-state]]
<!-- trace:end -->

## Notes

The `DEX active liquidity` pane still needs a feature computing a series from
these rows; this delivers the rows. §27.3's second pane remains on Phase 4's
`not_delivered` list until that exists.
