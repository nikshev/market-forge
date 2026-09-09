---
id: OUT-2026-09-09-implement-derivatives-context
step: implement
records: [REQ-EXP-006]
commit: null
---

## What was done

`channelflow.research.derivatives_context`: EXP-006's four conditionals, bucketed
by declared edges and scored by [[REQ-BT-001]]'s economics. 12 tests, ten
mutations, all caught on the first sweep.

## A fixture that agreed for the wrong reason

The thin-bucket test added three setups at a funding reading of 1.5 and asserted
the bucket holding them was too small to score. It failed: with the default edges
those three joined the twenty already sitting between 0 and 2, and the bucket had
twenty-three setups in it.

The test now declares an edge at 1.0 so the three have a bucket of their own.
The assertion was right, the fixture was not putting the code in the state the
assertion described — the same shape as the control price in [[REQ-EXP-005]] the
hour before.

## What was decided

- **Declared edges.** Sample quantiles look more sophisticated and make two
  studies incomparable.
- **A variable with no data is unavailable**, not one bucket holding everything.
- **The point-in-time flag is required and the note is generated from it**, so
  the label cannot drift from the fact.
- **A bucket too small carries its count and no score.**

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A variable with no data becomes one flat bucket | `test_a_variable_with_no_data_is_unavailable_not_a_flat_conditional` |
| The declared edges are ignored | `test_the_conditional_separates_the_buckets_it_should` (+1) |
| The low edge is not applied | `test_a_bucket_too_small_is_reported_and_not_scored` (+1) |
| The high edge is not applied | `test_a_bucket_too_small_is_reported_and_not_scored` (+1) |
| The small-bucket guard is dropped | `test_a_bucket_too_small_is_reported_and_not_scored` |
| Ambiguous outcomes are kept | `test_ambiguous_outcomes_are_excluded_and_counted` |
| The costs refusal is dropped | `test_the_study_without_costs_is_refused` |
| The point-in-time label is always predictive | `test_a_contemporaneous_study_says_so` |
| The costs are not passed to the buckets | `test_raising_the_costs_lowers_every_bucket` (+1) |
| A variable is dropped from the set | `test_all_four_variables_are_reported` (+1) |

## What is still open

- **Nothing produces the observations.** The study conditions on what it is
  given.
- **One variable at a time.** A joint conditional is a different experiment and
  a much hungrier one.
