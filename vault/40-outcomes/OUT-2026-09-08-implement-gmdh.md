---
id: OUT-2026-09-08-implement-gmdh
step: implement
records: [REQ-WP-018]
commit: null
---

## What was done

`channelflow.models`: the model protocol with two baselines, the layered
polynomial search, and PRD §23.6's comparison report. 21 tests, no new
dependencies.

This is the first ML layer in the repository, and Constitution Principle IV is
why it could not be written earlier.

## What was decided

- **The GMDH search beats logistic regression on an interaction target, and
  that is tested rather than assumed.** The fixture's label turns on
  `x0 * x1`, which no linear model can capture. A fixture where both did
  equally well would have proven nothing in either direction.
- **A second fixture is pure noise**, where the base rate is unbeatable by
  construction. It is what proves the search stops rather than growing to its
  budget — and `NO_IMPROVEMENT` is the stop reason it reports.
- **The split guard lives beside the protocol, not inside the search**, because
  the report needs it too: a comparison computed on training rows is the most
  flattering number in the system.
- **`Model.fit` raises for GMDH.** A single-split fit cannot be honestly
  provided, and inventing one inside would choose a rule PRD §41 rules 1 and 10
  are specifically about.
- **`_sigmoid` clips before exponentiating.** An unclipped `exp` overflows on a
  large magnitude and returns `nan`, which then propagates through every score
  in the report as a blank rather than as an error.

## The width-budget mutation had to be verified in isolation

Removing `survivors_per_layer` does not produce a wrong answer — it produces no
answer. Each layer's candidate count grows as C(n, 2), so four inputs become 6
nodes, then 15, then 105, then 5,460, and the suite stops responding rather
than failing. The sweep had to be killed and `gmdh.py` restored by hand.

Run alone, `test_the_width_budget_is_respected` fails in 0.34s, so the guard is
genuinely tested. But the episode is worth recording twice over: the width
budget is not a quality control, it is what makes the search terminate at all;
and a mutation harness needs a per-test timeout, because "the suite hung" and
"the suite passed" are equally uninformative about whether the guard works.

## Mutation results

Six mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Selection scores on the fitting split | `test_selection_uses_data_the_node_was_not_fitted_on` (+1) |
| Overlapping splits are allowed | `test_overlapping_splits_are_refused` (+1) |
| The search grows regardless of improvement | `test_the_search_stops_when_a_layer_stops_improving` |
| A tie counts as beating the base rate | `test_a_tie_with_the_base_rate_does_not_count_as_beating_it` |
| Unrun baselines are omitted from the report | `test_every_baseline_from_the_prd_appears_in_the_report` |
| The width budget is ignored | `test_the_width_budget_is_respected`, in isolation |

The first is GMDH's defining failure and it is silent: the search grows to its
budget, the model looks excellent, and every number downstream describes a
memorised sample. The test that catches it scores against a deliberately
contradictory target, so a node reading its own training rows cannot help but
look good.

## What is still open

- **Four of PRD §23.6's six baselines do not run** ([[ADR-029]]), and every
  report names them. A GMDH result here is not "validated" in §23.6's sense.
- **§13A.11's derivative hypothesis and §13A.12's root filtering** are not
  built; they carry [[REQ-NRT-F]] and belong to REQ-WP-019's ordering.
- **Nothing consumes the model.** No promotion gate, no signal integration.
- **The search is fitted, not calibrated.** PRD §23.8 asks for reliability
  diagrams and calibration drift beside the Brier score; only Brier is here.
