---
id: OUT-2026-09-09-implement-lookback-sensitivity
step: implement
records: [REQ-EXP-002]
commit: null
---

## What was done

`channelflow.research.lookback_sensitivity`: EXP-002's six lookbacks, the
plateau rule, and a recommendation that cannot be the peak. 14 tests.

## A test that never reached the branch it named

The sweep found three survivors, and the third is worth recording.

`test_an_unmeasurable_lookback_is_reported_and_the_rest_still_run` asserted that
some lookback came back with a reason and no expectancy. On a 400-bar series,
four of the six did — but because no setup confirmed out of sample, not because
the series was too short. The `SeriesTooShort` branch the test was written for
was never executed, and replacing its exception handler with an unrelated one
changed nothing.

A 280-bar series reaches it for the 200-bar lookback alone, and the test now
asserts *which* reason it got. Two absences that look alike in a field are two
different findings, and a test that accepts either is testing neither.

The other two survivors were the familiar shape: the recommendation's centre was
indistinguishable from its edge on a fixture whose plateau made them the same
candidate set, and the outer costs refusal was a restatement of the one inside
the comparison until it was tested with an empty sweep, where only the outer one
can fire.

## What was decided

- **No plateau means no recommendation**, and the peak is reported in its own
  field rather than substituted.
- **An absent value splits a plateau.**
- **Ties between equally wide plateaus go to the higher expectancy**, declared,
  rather than to whichever the scan reached first.

## Mutation results

Nine mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A run of one counts as a plateau | `test_a_single_lookback_is_not_a_plateau` (+1) |
| An absent value is skipped over | `test_an_absent_value_splits_a_plateau_rather_than_being_skipped` |
| The tolerance is ignored | `test_the_recommendation_comes_from_the_plateau_not_the_peak` (+1) |
| The plateau tie-break is dropped | `test_equally_wide_plateaus_are_broken_by_a_declared_rule` |
| The peak is recommended when there is no plateau | `test_with_no_plateau_nothing_is_recommended_and_the_peak_is_not_substituted` |
| The recommendation is the plateau's edge | `test_the_recommendation_is_the_middle_of_the_plateau_not_its_edge` |
| The costs refusal is dropped | `test_a_sweep_without_costs_is_refused` |
| An unmeasurable lookback ends the sweep | `test_a_lookback_the_series_cannot_hold_is_reported_and_the_rest_still_run` |
| The sweep drops a lookback | `test_all_six_lookbacks_are_swept` |

## What is still open

- **The tolerance is a research default.** It sets what "does not matter much"
  means, and PRD §13.11's warning about research defaults applies to it.
- **Nothing chooses a production lookback.** The experiment recommends; the
  decision has more inputs than one series.
