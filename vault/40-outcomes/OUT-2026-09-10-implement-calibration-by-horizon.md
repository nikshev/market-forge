---
id: OUT-2026-09-10-implement-calibration-by-horizon
step: implement
records: [REQ-WP-023, REQ-PHASE-7]
commit: null
---

## What was done

`calibration_by_horizon` in `models/metrics.py`, with `HorizonSlice`,
`HorizonCalibration` and two Protocols for the row shape. `calibration()` is
untouched.

10 new tests, 1570 in the suite, mypy clean at 167 files.

[[REQ-PHASE-7]]'s last unbuilt deliverable is closed and the phase reaches
`implemented` — **the fourth**, after [[REQ-PHASE-6]], [[REQ-PHASE-0]] and
[[REQ-PHASE-1]].

The test worth reading is `test_the_pooled_figure_hides_what_the_slices_show`:
one horizon well calibrated, one badly, and the pooled error landing between them
looking tolerable. That is the requirement's argument, executable.

## What the mutation sweep found

10 mutants, 9 caught, and the tenth was more useful than a catch.

- **The empty-input guard was a rule stated twice and owned by neither.**
  Deleting it changed nothing: `calibration()` refuses empty input with the same
  words one layer down. It is removed rather than tested, and the docstring says
  where the refusal lives.

The rest held, including the two that matter most: judging thinness on positive
outcomes instead of rows, and scoring a slice over every row instead of its own.

## What is still open

- **Nothing calls it yet.** `DirectBaselineResult` reports per-fold comparisons
  and no caller assembles rows with their probabilities to hand here. Wiring it
  into the turning-point experiment is a change to that module and belongs with
  whoever next touches it.
- **A per-row horizon would degenerate the report** into one slice per row.
  Visible rather than silent, and unwarned.
