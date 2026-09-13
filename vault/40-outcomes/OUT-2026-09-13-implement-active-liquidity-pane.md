---
id: OUT-2026-09-13-implement-active-liquidity-pane
step: implement
records: [REQ-WP-063]
commit: null
---

## What was done

`dex_active_liquidity` in `features/dex.py`, `read_states` on the state table,
and §27.3's ninth pane. 20 tests, **21 of 21 mutants caught**. All nine of PRD
§27.3's lower panes now exist.

## The rule is not the depth curve's, and that is the whole requirement

[[REQ-WP-060]] permits a §18.7.1 traversal only from `ANCHORED` and `REPLAYED`,
because a traversal walks the tick map. **This pane reads a different field.**

`active_liquidity` is the pool's own report, carried by every `Swap` and applied
verbatim, so it self-heals at the first swap of any window. A `PARTIAL_TICKS`
grade says the tick map is incomplete and says nothing about it.

    ANCHORED        usable
    REPLAYED        usable
    PARTIAL_TICKS   usable — the defect is elsewhere in the state
    GAPPED          not usable — not wrong, undated
    DIVERGED        not usable — contradicted at the state's own block

`GAPPED` is the interesting exclusion. It is not that the number is wrong: with
events missing, the last swap the replay saw may not be the last swap before the
row's own `state_time_ns`, so the row would date a reading it does not have. A
pane keyed by time cannot use that.

Two rules for two fields of one state, and a test asserts they differ rather than
letting one be copied from the other. Had the pane inherited `DEPTH_CAPABLE` it
would have discarded **every row [[REQ-WP-062]] writes today**, all of which are
`PARTIAL_TICKS`, and shown an empty pane for a pool whose liquidity is known
exactly.

## A float is right here and was wrong two requirements ago

§19 registers a feature's value as `float64` and the features table stores one.
Active liquidity is a `uint128` — 5481181047667912297 for the measured pool — and
a float64 drops its last digits.

That is acceptable **because it is a magnitude drawn as a line**. [[REQ-WP-061]]
converted every timestamp away from `number` for the opposite reason: there
`known_at_ns <= atNs` decides what a reader may see, and one part in 2⁵³ is the
difference between admitting and hiding a fact. Here it is smaller than a pixel.
The test asserts both halves — that the conversion does lose digits, and that the
relative error is under 1e-15 — so the claim is measured rather than assumed.

## What the pane will not claim

A concentrated-liquidity `L` depends on the pool's tick spacing and token
decimals, so it answers whether this pool is deeper than it was and not whether
it is deeper than another. The registration says so in `normalization`, and a
mutation removing that sentence is caught: §18A.4's
`volume-to-active-liquidity ratio` is the comparable form and needs a volume this
pane does not have.

## The third guard that was written to fail here

`test_no_active_liquidity_pane_is_offered` asserted this pane's absence and gave
its reason. It was written under [[REQ-WP-059]], survived [[REQ-WP-060]], and
failed here — the third time in four sessions that a test written to announce an
absence has been what announced the absence ending.
