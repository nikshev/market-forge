---
id: OUT-2026-09-09-implement-gmdh-extrema
step: implement
records: [REQ-EXP-013]
commit: null
---

## What was done

`channelflow.research.gmdh_extrema`: EXP-013's four arms, seven metrics and
rejection rule. 16 tests, fourteen mutations, all caught. `read_derivative_folds`
extracted from `run_derivative_experiment` so both callers share one promotion
loop; the 42 existing turning tests stayed green through it.

## A denominator that reversed the verdict

PRD §13A.12 defines the root presence rate over one root's perturbed members.
EXP-013 wants it over a whole experiment, and nobody wrote down which rows count.

Averaging over every scored row counts a row whose forward path never turned as
a root that went missing. On the first fixture built here — half the paths
straight by construction — that dragged the mean to exactly 0.50 against the
gate's 0.70, and the experiment reported "roots are unstable" about roots that
were stable in every member of every lattice. The failure is quiet: 0.50 is a
plausible-looking number and it moves with the fixture, so it reads as a finding.

The horizon IQR has the same trap running the other way. The gate reads it as a
*maximum*, a row with no root contributes no spread, and averaging that absence
in as zero halves the figure — an error in the direction that lets an unstable
set through. Both are now averaged over the rows that produced a root, with both
counts reported. [[ADR-051]].

## Two survivors, and two fixtures that could not see

The sweep found two, and both were denominators no fixture could reach.

The horizon IQR halved without failing anything, because no test named the
number. It does now, and the reference is the production stability function's
own answer for the fixture's own path — not a figure written into the test.

And no fixture contained a call whose true forward path never turned, because
every fixture's paths were a clean function of its features, so the coefficient
networks reproduced them exactly. Keying the paths to a period neither feature
follows makes the networks predict the average path, which turns: 41 of 64 calls
then land on rows with nothing to be wrong about. Scoring those as zero error
would reward an arm for calling turns on paths that never turn, so the three
counts — compared, without truth, called without a root — now have to add up to
the calls.

## What was decided

- **A classifier arm reports no time-to-turn error and no extreme-price error.**
  It never named a time. That blank is the comparison.
- **The ensemble is the mean of its members, not their product.** A product is
  zero wherever no root was promoted, silencing the ensemble on exactly the rows
  where the classifier is the only thing speaking.
- **A called row with no recorded outcome raises.** Dropping it would price the
  arm on the subset of its calls someone happened to resolve.
- **The verdict names every failure.** One reason at a time costs a full re-run
  per reason.

## Mutation results

Fourteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An arm is dropped from the comparison | `test_all_four_arms_the_prd_names_are_compared` |
| A classifier arm is scored on a time and a price | `test_a_classifier_arm_names_no_time_and_no_price` |
| The presence rate is averaged over every row | `test_the_presence_rate_is_averaged_over_the_rows_that_had_a_root` |
| The horizon IQR is averaged over every row | `test_the_horizon_iqr_is_the_spread_of_the_roots_that_exist` |
| The stability half of the verdict is dropped | `test_unstable_roots_are_rejected` |
| The value half of the verdict is dropped | `test_a_derivative_arm_that_adds_nothing_is_rejected` |
| The verdict stops at the first failure | `test_both_reasons_are_reported_when_both_fail` |
| The ensemble is the product, not the mean | `test_the_ensemble_keeps_its_classifier_half` |
| A called row with no outcome is skipped | `test_a_called_row_without_an_outcome_is_refused` |
| The increment is measured against nothing | `test_the_increment_is_measured_against_the_direct_classifier` |
| The baseline gets an increment of its own | `test_the_increment_is_measured_against_the_direct_classifier` |
| The call threshold is unbounded | `test_the_call_threshold_is_required_and_bounded` |
| A row without a true turn counts as a miss | `test_a_call_with_no_true_turn_is_counted_rather_than_scored` |
| A call with no root behind it is dropped silently | `test_the_ensemble_keeps_its_classifier_half` |

## What is still open

- **No arm is selected for production.** The fixtures here are synthetic by
  construction — one of them exists precisely because no linear model can learn
  it — and they establish that the comparison can conclude either way, not what
  it concludes on real bars.
- **The call threshold is unvalidated**, and every economic figure moves with it.
- **The ensemble's weighting is a flat mean.** Weighting the two halves is a
  research question this experiment does not open.
