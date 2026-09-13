---
id: REQ-WP-063
title: The active liquidity pane draws the rows that can carry it
type: work-package
prd_ref: "§27.3, §18.12.2, §18A.4, §19"
prd_lines: "4423-4436, 3177-3193, 3712-3721, 3764-3800"
phase: 4
status: implemented
depends_on: [REQ-WP-062, REQ-WP-060, REQ-WP-059]
tags: []
---

## Requirement

PRD §27.3 lists nine lower panes. Eight exist; the ninth is `DEX active
liquidity`, and it has been absent through three requirements because nothing
produced the number. [[REQ-WP-060]] put `active_liquidity` on a canonical row
and [[REQ-WP-062]] gave that table a producer, so the data now exists and no
feature reads it.

### The quality rule here is not the depth curve's

[[REQ-WP-060]] permits a §18.7.1 traversal only from `ANCHORED` and `REPLAYED`,
because the tick map is what a traversal walks. **This pane reads a different
field, and the rule is therefore different** — which is exactly why it has to be
stated rather than inherited.

    ANCHORED        usable
    REPLAYED        usable
    PARTIAL_TICKS   usable — the defect is the tick map; active liquidity is
                    the pool's own report from its last swap and self-heals
    GAPPED          not usable — events are missing, so the last swap the replay
                    saw may not be the last swap before `state_time_ns`, and the
                    row would date a reading it does not have
    DIVERGED        not usable — a contract read at the state's own block
                    contradicted the state

A pane that inherited the traversal's rule would discard every `PARTIAL_TICKS`
row, which today is every row [[REQ-WP-062]] writes, and show an empty pane for a
pool whose liquidity is known exactly. A pane that ignored quality altogether
would draw `GAPPED` rows as though they were current.

### The value is a magnitude, and floats are allowed here

§19 registers a feature's value as `float64` and the features table stores one.
Active liquidity is a `uint128` — 5481181047667912297 for the measured pool —
and a float64 cannot hold it exactly.

That is acceptable **because it is a magnitude drawn as a line**, not an instant
a comparison turns on. [[REQ-WP-061]] converted every timestamp for the opposite
reason: `known_at_ns <= atNs` decides what a reader may see, and one part in 2⁵³
there is the difference between admitting and hiding a fact. One part in 2⁵³ of a
liquidity figure is invisible at any pixel. The distinction is stated in the
registration rather than left for a reader to rediscover.

### Pool-internal, and not comparable across pools

A concentrated-liquidity `L` is denominated in the pool's own units and depends
on its tick spacing and token decimals. It answers "is this pool deeper than it
was" and not "is this pool deeper than that one", and the registration says so:
§18A.4's `volume-to-active-liquidity ratio` is the comparable form and needs a
volume this pane does not have.

## Acceptance

- `dex_active_liquidity` is registered with §19's sixteen fields, declares
  `point_in_time_safe`, and its `normalization` states that it is pool-internal.
- A reading is taken from the most recent usable row at or before the instant
  asked for; a later row is never used.
- `PARTIAL_TICKS` rows are usable and `GAPPED` and `DIVERGED` rows are not, each
  asserted by name rather than by membership in a set copied from elsewhere.
- A window whose only rows are unusable yields no value — not zero, and not the
  last usable row from before the window.
- `panes.ts` offers the pane, and Phase 4's ninth pane leaves the list.
- The float64 conversion is exercised on the measured `uint128`, and the loss is
  asserted to be below what a pane can show.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-104-active-liquidity-pane]]
- **Tests:**
    - `tests/unit/features/test_dex.py::test_a_grade_that_cannot_date_or_be_trusted_is_not_read[diverged]`
    - `tests/unit/features/test_dex.py::test_a_grade_that_cannot_date_or_be_trusted_is_not_read[gapped]`
    - `tests/unit/features/test_dex.py::test_a_partial_tick_map_still_carries_the_liquidity`
    - `tests/unit/features/test_dex.py::test_a_reading_exactly_at_the_instant_is_visible`
    - `tests/unit/features/test_dex.py::test_an_unusable_newer_row_does_not_hide_a_usable_older_one`
    - `tests/unit/features/test_dex.py::test_no_usable_row_yields_no_value`
    - `tests/unit/features/test_dex.py::test_the_float_loses_only_what_a_pane_cannot_show`
    - `tests/unit/features/test_dex.py::test_the_newest_usable_reading_at_or_before_the_instant_wins`
    - `tests/unit/features/test_dex.py::test_the_registration_says_it_is_not_comparable_across_pools`
    - `tests/unit/features/test_dex.py::test_the_usable_grades_are_named_and_are_not_the_traversals`
    - `tests/unit/features/test_pane_features.py::test_every_pane_prd_section_27_3_lists_is_offered`
    - `tests/unit/features/test_pane_features.py::test_the_active_liquidity_pane_is_offered`
    - `tests/unit/tables/test_dex_state.py::test_a_state_computed_after_the_instant_asked_for_is_not_returned`
    - `tests/unit/tables/test_dex_state.py::test_a_state_reads_back_with_its_big_integers_as_integers`
    - `tests/unit/tables/test_dex_state.py::test_states_are_filtered_by_pool`
- **Code:**
    - `apps/web/src/panes.ts`
    - `src/channelflow/features/dex.py`
    - `src/channelflow/tables/dex_state.py`
- **Outcomes:** [[OUT-2026-09-13-implement-active-liquidity-pane]]
<!-- trace:end -->

## Notes

Every row [[REQ-WP-062]] writes today is `PARTIAL_TICKS`, because an `ANCHORED`
row needs a replay from a pool's first initialised block or a checkpoint read.
The pane therefore works on exactly the rows that exist, and the rule above is
what makes that honest rather than convenient.
