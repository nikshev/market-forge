---
id: REQ-WP-060
title: A reconstructed pool state knows how much of itself it knows
type: work-package
prd_ref: "§18.12.2, §18.7.2, §18.24, §18.25"
prd_lines: "3177-3193, 2894-2902, 3550-3565, 3568-3590"
phase: 4
status: implemented
depends_on: [REQ-WP-015, REQ-WP-053, REQ-WP-054]
tags: []
---

## Requirement

PRD §18.12.2's `LiquidityState` ends with a field nothing in this repository
produces:

    model_type
    active_liquidity nullable
    reserve_state nullable
    invariant_state nullable
    fee_state
    finality_status
    reconstruction_quality

§18.24's adapter protocol asks for it as a method — `def quality(self, state) ->
ReconstructionQuality` — and there is no such type.

[[REQ-WP-015]] already reconstructs the state. `dex/pool.py` applies §18.7's
ordered events, keeps §18.7.1's sparse `tick -> liquidity_net` map, refuses a
duplicate log and refuses negative liquidity, and `compare_with_contract`
implements §18.7.2's divergence check. **What is missing is not the
reconstruction. It is the reconstruction's opinion of itself.**

### Why that is the load-bearing part

Active liquidity self-heals: `_apply_swap` takes the pool's own reported
`liquidity`, so a replay that started anywhere converges on the right number at
the first swap.

**The tick map does not self-heal.** It accumulates only the mints and burns the
replay actually saw. A range initialised before the replay window is invisible,
and §18.7.1's traversal walks that map to build the depth curve — so a partial
map yields a curve that is ordered, positive, monotone and describes a pool far
thinner than the real one.

**This collides with [[ADR-036]].** That decision separated a band the walk
reached from one where the book ran out, precisely so a thin pool could not read
as a cheap one. From a partial tick map the walk runs out for a second reason —
*our knowledge* ended, not the liquidity — and the two produce the identical
band. [[REQ-WP-059]] has just put those bands on a chart, where "exhausted at 17
bps" now reads as a fact about the market.

### Measured on the chain, not asserted

The detection is the pool's own arithmetic. In a concentrated-liquidity pool the
liquidity at the current tick is the running sum of `liquidity_net` over every
initialised tick at or below it, so a complete map satisfies

    sum(liquidity_net for tick <= current_tick) == active_liquidity

and the two sides come from different events: mints and burns on the left, the
swap's own report on the right. A disagreement proves the map incomplete with no
archive node, no checkpoint and nobody's word for it. Equality does not strictly
prove completeness — errors could cancel — and that is stated rather than
implied.

Measured on the fixture: implied liquidity **0** against a reported
5481181047667912297, so the traversal would have run over none of the pool.

**One thing must still be asserted.** A block containing no `Mint` is
indistinguishable from a block whose `Mint` was not fetched, so whether the
replayed range has holes is known only to whoever read the chain.

### §18.7.2's own check cannot see this

The recovery comparison looks at the three scalars a swap already reports. On the
measured state two matched the contract exactly and the third differed by 1.4e-8
relative — under a thousandth of a basis point of price, being drift over the
blocks between the last swap and the read. A reader would call that noise, and be
right. The empty tick map is invisible to it because it never looks there.

### The classes

Derived, not quoted — §18.12.2 names the field and never enumerates it. Each
class is a statement about what the state may be used for:

    ANCHORED        the map accounts for the liquidity, and a read at the
                    state's own block agreed
    REPLAYED        the map accounts for the liquidity
    PARTIAL_TICKS   it does not: scalars may be exact, the curve is not the pool's
    GAPPED          the replayed range has holes
    DIVERGED        a read at the state's own block disagreed

A reconciliation taken at a *different* block is not evidence either way: a
contract read later than the state disagrees with a correct reconstruction
whenever anything traded in between, and counting it is how a real check becomes
noise.

§18.7.2 says never silently patch historical derived rows, so `DIVERGED` is a
recorded state and not a correction.

**A depth curve may be computed from `ANCHORED` and `REPLAYED` only.** The other
three are the cases where the traversal would answer from a map it cannot vouch
for, and a refusal is the only honest output — the same rule [[REQ-WP-047]]
applies to `CUSTOM_ACCOUNTING` pools, for the same reason.

**That needs two guards, not one.** A `PoolState` carries no provenance, so the
traversal can check the invariant and nothing else; a `GAPPED` reconstruction
whose surviving events happen to balance passes it. The gap is caught by a
second gate, where the provenance exists. One guard would have had to take the
other's input on trust.

## Acceptance

- `ReconstructionQuality` exists with the five classes above, derived from a
  provenance record and never from the event list alone.
- A state whose tick map does not account for its reported liquidity is
  `PARTIAL_TICKS` however exact its scalars are — demonstrated on a replay whose
  tick and liquidity equal the contract's own.
- A state whose replayed range has a hole is `GAPPED`, including when its
  surviving events balance, and a contiguous range over quiet blocks is not.
- A reconciliation at the state's own block that disagrees yields `DIVERGED`; one
  taken at another block yields neither `DIVERGED` nor `ANCHORED`.
- `depth_to_bps` and `depth_curve` refuse a state whose tick map cannot explain
  it, and the refusal carries both liquidity figures rather than returning a
  short curve.
- The quality gate refuses `PARTIAL_TICKS`, `GAPPED` and `DIVERGED` by name, and
  covers the gap the traversal cannot see.
- Liquidity minted exactly at the current tick counts toward the liquidity at
  spot.
- §18.25 item 4: replaying from a checkpoint and replaying the whole range reach
  the same state.
- `LiquidityState` exists as a canonical table carrying §18.12.2's fields, with
  `reconstruction_quality` among them.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-101-pool-state-quality]]
- **Tests:**
    - `tests/unit/dex/test_reconstruction.py::test_a_balanced_map_with_no_reconciliation_is_replayed`
    - `tests/unit/dex/test_reconstruction.py::test_a_curve_is_refused_rather_than_reported_as_a_thin_pool`
    - `tests/unit/dex/test_reconstruction.py::test_a_disagreement_at_the_states_own_block_is_a_divergence`
    - `tests/unit/dex/test_reconstruction.py::test_a_gap_is_reported_even_when_the_map_is_also_partial`
    - `tests/unit/dex/test_reconstruction.py::test_a_gap_outranks_a_map_that_happens_to_balance`
    - `tests/unit/dex/test_reconstruction.py::test_a_hundred_block_replay_matches_the_contract_on_every_scalar`
    - `tests/unit/dex/test_reconstruction.py::test_a_pool_with_no_liquidity_is_not_a_partial_reconstruction`
    - `tests/unit/dex/test_reconstruction.py::test_a_range_backwards_is_refused`
    - `tests/unit/dex/test_reconstruction.py::test_a_reconciliation_at_another_block_is_not_evidence`
    - `tests/unit/dex/test_reconstruction.py::test_an_agreeing_reconciliation_at_the_states_own_block_anchors_it`
    - `tests/unit/dex/test_reconstruction.py::test_and_its_tick_map_explains_none_of_that_liquidity`
    - `tests/unit/dex/test_reconstruction.py::test_liquidity_minted_exactly_at_spot_counts`
    - `tests/unit/dex/test_reconstruction.py::test_only_anchored_and_replayed_may_be_traversed`
    - `tests/unit/dex/test_reconstruction.py::test_replaying_in_two_halves_reaches_the_same_state`
    - `tests/unit/dex/test_reconstruction.py::test_the_quality_does_see_it`
    - `tests/unit/dex/test_reconstruction.py::test_the_recovery_check_cannot_see_it`
    - `tests/unit/dex/test_reconstruction.py::test_the_two_guards_cover_different_ground`
    - `tests/unit/dex/test_reconstruction.py::test_whether_the_old_guard_catches_a_partial_replay_is_luck`
    - `tests/unit/tables/test_dex_state.py::test_a_negative_implied_liquidity_keeps_its_sign`
    - `tests/unit/tables/test_dex_state.py::test_a_state_survives_the_round_trip`
    - `tests/unit/tables/test_dex_state.py::test_every_quality_is_writable_as_a_string`
    - `tests/unit/tables/test_dex_state.py::test_liquidity_beyond_int64_survives`
    - `tests/unit/tables/test_dex_state.py::test_the_columns_with_no_producer_are_absent_rather_than_null`
    - `tests/unit/tables/test_dex_state.py::test_the_models_without_a_producer_are_null_not_empty`
    - `tests/unit/tables/test_dex_state.py::test_the_replayed_range_is_on_the_row`
    - `tests/unit/tables/test_dex_state.py::test_the_row_carries_the_evidence_for_its_own_quality`
- **Code:**
    - `src/channelflow/dex/reconstruction.py`
    - `src/channelflow/tables/dex_state.py`
    - `tools/record/pool_state_capture.py`
- **Outcomes:** [[OUT-2026-09-13-implement-pool-state-quality]]
<!-- trace:end -->

## Notes

On HyperEVM the read an `ANCHORED` state needs cannot be taken at a historical
block at all: the public endpoints are not archive nodes ([[ADR-067]]). On
Ethereum it can, and the fixture records the contrast as a measurement — the
same `eth_call` agreed with the logs exactly. That difference is a property of
the available endpoints rather than of this code, which is why the quality is a
value on the row instead of a global assumption.

[[REQ-WP-015]]'s `NegativeLiquidity` already refuses *some* partial replays: it
fires when a burn happens to touch a range minted before the window. Both
behaviours are in this one fixture — silent below 200 blocks, raising above 400 —
so whether the old guard catches it is luck, and an exception is not a value a
row can carry either way.
