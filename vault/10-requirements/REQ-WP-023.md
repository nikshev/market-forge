---
id: REQ-WP-023
title: Turning-point probabilities are calibrated per horizon, not in aggregate
type: work-package
prd_ref: "§23.5A, §23.8, §45 Phase 7"
prd_lines: "4065-4074, 6861"
phase: 7
status: implemented
depends_on: [REQ-WP-018, REQ-WP-019, REQ-US-007]
tags: []
---

## Requirement

PRD §23.5A defines Target E as three classes, each conditioned on an explicit
horizon:

    Classification by explicit horizon `H`:

    P(local_max_within_H | point_in_time_state)
    P(local_min_within_H | point_in_time_state)
    P(no_turn_within_H | point_in_time_state)

PRD §45's Phase 7 asks for "P(max)/P(min)/P(no-turn) calibration by horizon",
and §7 item 14 requires a turning-point forecast to "expose explicit horizon and
calibrated `P(max)/P(min)/P(no-turn)`".

`calibration()` exists and reports one curve over every prediction it is given.
Nothing slices it.

**Why aggregate calibration is the wrong number here.** A forecast is only
usable at a stated horizon, and a model's reliability is not constant across
them: five bars ahead is nearly the present, fifty is a different question about
a different market. A model well calibrated at short horizons and badly at long
ones reports an acceptable aggregate — the average is dragged toward the horizon
with the most rows, which is a fact about the dataset rather than about the
model. The failure the aggregate hides is precisely the one that matters,
because a trader acts at one horizon and not at the average of several.

## Acceptance

- calibration is reported per horizon and per target class, never only pooled;
- a horizon with too few observations to say anything is reported as unmeasured
  rather than as a curve — an absent reliability and a poor one are different
  facts;
- the horizon of a row is derived from its own label rather than supplied
  alongside it, so a caller cannot mislabel one;
- a pooled figure, where reported, is reported beside its slices and never
  instead of them;
- an existing caller of `calibration()` keeps the number it had.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-062-calibration-by-horizon]]
- **Tests:**
    - `tests/unit/models/test_calibration_by_horizon.py::test_a_misaligned_pair_is_refused`
    - `tests/unit/models/test_calibration_by_horizon.py::test_a_report_is_a_value`
    - `tests/unit/models/test_calibration_by_horizon.py::test_a_target_that_never_occurs_is_measured_not_unmeasured`
    - `tests/unit/models/test_calibration_by_horizon.py::test_a_thin_horizon_is_unmeasured_rather_than_curved`
    - `tests/unit/models/test_calibration_by_horizon.py::test_each_horizon_gets_its_own_curve`
    - `tests/unit/models/test_calibration_by_horizon.py::test_no_rows_is_refused`
    - `tests/unit/models/test_calibration_by_horizon.py::test_the_horizon_comes_from_the_row_s_own_label`
    - `tests/unit/models/test_calibration_by_horizon.py::test_the_minimum_is_the_caller_s`
    - `tests/unit/models/test_calibration_by_horizon.py::test_the_pooled_figure_hides_what_the_slices_show`
    - `tests/unit/models/test_calibration_by_horizon.py::test_the_pooled_figure_is_what_calibration_would_have_said`
- **Code:**
    - `src/channelflow/models/metrics.py`
- **Outcomes:** [[OUT-2026-09-10-implement-calibration-by-horizon]], [[OUT-2026-09-10-plan-calibration-by-horizon]], [[OUT-2026-09-10-requirement-calibration-by-horizon]], [[OUT-2026-09-10-spec-calibration-by-horizon]]
<!-- trace:end -->

## Notes

This is the last entry in [[REQ-PHASE-7]]'s `not_delivered`.

Unlike the two deliverables closed earlier today, this one has a PRD section
behind it — §23.5A names the three classes and the conditioning, and §23.8 names
what a calibration report contains. What is derived here is only the treatment of
a thinly-populated horizon, and the derivation is the paragraph above: the whole
point of slicing is to stop an average speaking for a slice, so a slice that
cannot speak must say so rather than borrow the average's voice.

**Producing the forecasts is not in scope.** PRD §23.5B's time-and-price
regression and the forecast record of §12 are separate; this is about how a
probability that already exists is reported.
