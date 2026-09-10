---
id: REQ-WP-031
title: Long/short positioning is ingested, and its absence stays visible
type: work-package
prd_ref: "§16, §45 Phase 3"
prd_lines: "1778, 6767"
phase: 3
status: implemented
depends_on: [REQ-WP-013, REQ-WP-026]
tags: []
---

## Requirement

PRD §45's Phase 3 lists "optional long/short stats;" and PRD §16's derivatives
feature list names what they are for:

    - long/short squeeze context where available.

Three words carry the requirement. **Squeeze context** is not the ratio: a
crowded book is a condition, and a number without a sense of how unusual it is
says nothing about crowding. **Where available** is the other half: not every
venue publishes positioning, and a market that does not publish it is not a
balanced market.

`DerivativesState` carries funding, open interest and basis, and nothing about
who is positioned which way. It is the last entry in [[REQ-PHASE-3]]'s
`not_delivered`.

## Acceptance

- a venue's long/short account ratio and top-trader ratio are carried on
  derivatives state, each optional;
- a ratio nobody published reads as absent, never as balanced — a ratio of 1.0
  is a real reading and means the opposite of an unknown one;
- the crowding reading is relative to the instrument's own recent positioning,
  not to a constant: a ratio of 2.0 is ordinary on one instrument and extreme on
  another;
- a reading refuses rather than guessing when there is too little history to say
  what is unusual;
- the features are registered like every other, with their null policy stated;
- a stale positioning reading is refused, as [[REQ-WP-026]] refuses a stale
  funding one — the same REST polling, the same failure;
- nothing that exists changes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-069-long-short]]
- **Tests:**
    - `tests/unit/derivatives/test_positioning.py::test_a_non_positive_ratio_is_refused[-1.0]`
    - `tests/unit/derivatives/test_positioning.py::test_a_non_positive_ratio_is_refused[0.0]`
    - `tests/unit/derivatives/test_positioning.py::test_a_ratio_nobody_published_reads_as_nothing`
    - `tests/unit/derivatives/test_positioning.py::test_a_stale_reading_is_refused`
    - `tests/unit/derivatives/test_positioning.py::test_a_venue_that_publishes_nothing_is_not_a_balanced_market`
    - `tests/unit/derivatives/test_positioning.py::test_a_venue_that_stopped_publishing_positioning_is_stale`
    - `tests/unit/derivatives/test_positioning.py::test_no_state_at_all_is_its_own_refusal`
    - `tests/unit/derivatives/test_positioning.py::test_states_without_a_ratio_do_not_enter_the_history`
    - `tests/unit/derivatives/test_positioning.py::test_the_count_travels_with_the_reading`
    - `tests/unit/derivatives/test_positioning.py::test_the_history_stops_at_the_instant_being_asked_about`
    - `tests/unit/derivatives/test_positioning.py::test_the_latest_published_ratio_is_the_current_one`
    - `tests/unit/derivatives/test_positioning.py::test_the_new_features_are_registered_with_a_null_policy`
    - `tests/unit/derivatives/test_positioning.py::test_the_same_ratio_is_unusual_on_one_history_and_ordinary_on_another`
    - `tests/unit/derivatives/test_positioning.py::test_the_top_trader_ratio_has_its_own_reading`
    - `tests/unit/derivatives/test_positioning.py::test_the_two_ratios_are_independent`
    - `tests/unit/derivatives/test_positioning.py::test_too_little_history_is_refused_rather_than_called_average`
- **Outcomes:** [[OUT-2026-09-10-implement-long-short]], [[OUT-2026-09-10-plan-long-short]], [[OUT-2026-09-10-requirement-long-short]], [[OUT-2026-09-10-spec-long-short]]
<!-- trace:end -->

## Notes

**"Optional" describes the venue, not the rigour.** The PRD calls the stats
optional because a venue may not publish them. It does not follow that a feature
built on them may be sloppy about saying so — the opposite: a field that is
sometimes absent is exactly the field where an absent value silently becoming a
neutral one does the most damage, because nothing downstream will ever see a
gap.

**The squeeze reading is a z-score, and it refuses.** [[ADR-026]] settled that
for funding and open interest: zero is the most meaningful value a z-score can
take, and a feature that says "exactly average" whenever it has nothing to say
reads as a calm market to everything downstream. Positioning gets the same
treatment through the same shared function rather than a second one.
