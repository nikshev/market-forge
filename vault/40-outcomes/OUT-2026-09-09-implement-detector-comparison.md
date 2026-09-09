---
id: OUT-2026-09-09-implement-detector-comparison
step: implement
records: [REQ-EXP-003]
commit: null
---

## What was done

`WickOnly` and `TwoBarConfirmation` at REQ-WP-007's plugin point, and
`channelflow.research.detector_comparison` running all four through the
production machine. 20 tests.

## A metric no fixture could reach

Four mutations survived the first sweep. Three were ordinary fixture gaps — the
lag was never checked against zero, the wick detector was never tested on a long
setup, and expectancy's out-of-sample restriction was never compared against the
run's total.

The fourth was different. Hard-coding "the share of confirmations the market
later took back" to zero changed no test, because no bar series tried drives the
machine down that path: the candidate must reach `CONFIRMED` and then invalidate,
and several deliberately violent fixtures produced no confirmations at all.

Manufacturing a series until one appeared would have been a fixture built to
satisfy a sweep. Instead the measurement was split from the run: `detector_metrics`
takes candidate lives, and the metric is tested on lives that describe exactly
one taken-back confirmation out of two. The split is also the honest record of
which metrics the market fixtures cover and which one does not.

## What was decided

- **The order-flow detector is named and never scored.** Its inputs do not exist
  at the interface it would use.
- **Four metrics, not one score.** A detector can win on lag and lose on
  expectancy, and the report says so in its own note.
- **No second engine.** A test asserts the module builds no transition; PRD
  §25.2 forbids the copy and this is what makes that checkable.

## Mutation results

Thirteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The unavailable detector is dropped from the report | `test_all_four_detectors_appear_in_the_report` (+1) |
| The unavailable detector is ranked | `test_the_unavailable_detector_is_named_and_never_scored` (+1) |
| The ranking is worst-first | `test_the_ranking_is_by_expectancy_and_excludes_the_unscored` |
| A detector that confirms nothing reports zero | `test_a_detector_that_confirms_nothing_is_reported_with_its_reason` |
| The later-invalidation share is a constant | `test_the_taken_back_share_reaches_the_report` |
| The lag is measured from confirmation to itself | `test_the_lag_is_the_distance_from_opening_to_confirmation` |
| Expectancy includes in-sample confirmations | `test_expectancy_counts_only_out_of_sample_confirmations` |
| The costs refusal is dropped | `test_the_comparison_without_costs_is_refused` |
| The wick detector ignores the body | `test_the_wick_detector_reads_the_bar_the_prd_describes` |
| The wick detector ignores direction | `test_the_wick_detector_reads_the_lower_wick_for_a_long` |
| A bodyless bar is not a rejection | `test_a_bodyless_bar_with_a_wick_is_a_rejection_not_a_division_by_zero` |
| The two-bar detector answers on its first bar | `test_the_two_bar_detector_cannot_answer_on_its_first_bar` |
| The two-bar detector ignores direction | `test_the_two_bar_detector_refuses_a_higher_close` |

## What is still open

- **Order-flow confirmation.** Reported as unavailable until the detector
  protocol carries order flow — a change to [[REQ-WP-007]], not to this
  experiment.
- **No bar fixture produces a taken-back confirmation.** The metric is tested at
  the level where it can be, and this note is the record that the end-to-end path
  is not exercised.
