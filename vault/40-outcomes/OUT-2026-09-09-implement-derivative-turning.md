---
id: OUT-2026-09-09-implement-derivative-turning
step: implement
records: [REQ-EXP-012]
commit: null
---

## What was done

`channelflow.research.derivative_turning`: EXP-012's four causal candidates,
scored against centred labels at four horizons. 12 tests, nine mutations, all
caught.

## A protocol stricter than its own reference implementation

`Transform` declared `name: str` and `centered: bool` as attributes, which means
settable ones. `CausalTransform` — the class this package ships *as* the causal
transform — is a frozen dataclass and could not satisfy it. So the protocol
excluded the one type it exists to describe, and any frozen transform written
against it would have failed `mypy --strict` for being correct. They are
read-only properties now.

## Three survivors, and two fixtures that could not see

The sweep found three.

The first was the right edge. Moving the local polynomial's read point from
`x[-1]` to the window's centre changed no test, because the fixture asked about
the peak itself — where a nine-bar window holds nine bars of rise and both
readings are +1.0. Three bars past the peak they separate: the right edge has
turned to -0.46 while the centre still reads +0.63. Only the first number exists
at that bar, and that is where the test now looks.

The second was the horizon. Dropping it from the arithmetic entirely — scoring
only against the two-bar tolerance — changed nothing, because on a swing series
three of the four methods score 1.0 at every horizon and the fourth varies only
between 0.05 and 1.0 in a way no assertion pinned. Four horizons that cannot
differ are one measurement printed four times. A triangle with a single labelled
turn and a method that calls exactly eight bars early separates them: zero at 3
and 6, one at 12 and 24.

The third was half of the report's note. The test asked for "cannot run live"
and the note says three things; removing the clause that names the centred
filter left the assertion passing. It asks for both now, because either alone is
misreadable — "cannot run live" without "centred filter" reads as a caveat about
the candidates, and "centred filter" without it reads as a description of the
method under test.

## What was decided

- **Precision, not recall.** A method that calls every bar a turn has perfect
  recall and no information; precision is what a reader of an alert experiences.
- **Absent, not zero**, for a method that called nothing. A silent method is not
  a wrong one.
- **No Savitzky-Golay-equivalent candidate.** Its one-sided form is the causal
  local polynomial already here; its centred form is a label maker.
- **Nothing is ranked.** The comparison reports; the horizons and the call rates
  pull against each other and a winner would hide that.

## Mutation results

Nine mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A centred candidate is accepted | `test_a_centred_candidate_is_refused` |
| The labeller does not declare itself centred | `test_the_labeller_declares_itself_centred` |
| The local polynomial reads the window's centre | `test_a_local_polynomial_reads_the_right_edge_of_its_window` |
| Precision over no calls is zero | `test_precision_is_absent_for_a_method_that_calls_nothing` |
| The horizon is ignored | `test_a_call_beyond_the_tolerance_counts_only_at_the_longer_horizons` |
| A horizon is dropped | `test_every_horizon_the_prd_names_is_evaluated` |
| The report hides how the labels were made | `test_the_labels_are_made_by_a_centred_filter_and_the_report_says_so` |
| Every bar counts as a call | `test_a_smoother_method_calls_fewer_turns_than_the_raw_one` |
| The causality guard lets a centred transform through | `test_the_refusal_comes_from_the_production_guard` |

## What is still open

- **No estimator is selected for production.** The experiment reports precision
  on synthetic series; choosing needs real bars across regimes.
- **The two-bar tolerance is unvalidated.** It is a research default and it moves
  every number in the report.
