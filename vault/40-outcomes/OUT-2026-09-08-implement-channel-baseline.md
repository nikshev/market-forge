---
id: OUT-2026-09-08-implement-channel-baseline
step: implement
records: [REQ-WP-006]
commit: null
---

## What was done

All 14 tasks. Baseline A from PRD §13.2 in three modules, 20 tests, 229 in the
suite, `mypy --strict` clean over 20 source files.

**RED first for each phase**: `ModuleNotFoundError` for the channels package,
then failures for the fit, then for quality.

## The three mutations that matter, and what each proves

| Mutation | Caught by |
|---|---|
| remove the `as_of` filter — the model peeks | `test_bars_after_as_of_are_excluded_not_trusted`, and two others |
| stop excluding unfinalized bars | `test_unfinalized_bars_are_excluded` |
| default an unavailable submetric to 0.5 instead of omitting it | `test_unavailable_submetrics_are_omitted_not_defaulted` |

The first is the one this requirement exists for. A channel fitted with
hindsight looks superb, which is exactly why Principle I says the rule holds
"even when violating it would improve a backtest".

## A real numerical defect, found by the degenerate case

On a perfectly flat series the residuals are floating-point dust from the fit —
around 1e-16 — and dividing the slope by that spread produced
`slope_normalized = 0.088`. **A reported trend that does not exist**, on a series
that never moved.

Fixed with an explicit floor: below 1e-9 in log space there is no measurable
noise, so the ratio has nothing to divide by and is zero. Log prices run from
about 1 to 12, so that threshold sits far below any real price movement and far
above the fit's own rounding. The number is named in the module rather than
inlined, because a bare `1e-9` in a comparison is a magic constant nobody can
evaluate.

## Two defects in my own tests, worth recording

Both looked like model bugs and were not:

- The series helper always started at index 0, so the "future" bars appended in
  the repainting test **reused the original timestamps** and landed inside the
  window. The test would have passed for the wrong reason had the arithmetic
  worked out differently.
- The unfinalized-bar test compared against a fit that still contained the bar.
  Excluding a bar shifts the window by one; the correct comparison is against a
  history that genuinely lacks it.

## What was decided

- **Three filters, each a requirement rather than a precaution**: finalized only
  (PRD §12), at or before `as_of` (§13.1), and ordered by event time. All three
  live in the model, so a caller cannot forget one.
- **The invariant is validated in the snapshot as well as the fitter.** A
  snapshot constructed by any other route still cannot claim to have seen the
  future.
- **`forecast_horizons` is empty, not fabricated.** PRD §13.1 carries the field
  and §13.7 defines the content; this is Baseline A, and an honest absence beats
  a plausible-looking list.

## What is still open

- **The quality weights are equal, deliberately** — a refusal to pretend we know
  which submetric matters before anything has been measured. PRD §48's research
  questions come first, and §13.9 replaces the transparent average with ML
  scoring later.
- **Three submetrics remain uncomputable**: forecast calibration needs §13.8,
  regime compatibility needs §20, age needs channel-lifetime tracking.
- **Baselines B through E** (§13.3-13.6) are separate models behind the same
  interface, unbuilt.
- **No persistence.** Immutability honours §0.5 without a storage layer; §29.6's
  table is later.
