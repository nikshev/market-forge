---
id: OUT-2026-09-08-implement-turning-derivative
step: implement
records: [REQ-WP-019, REQ-NRT-F]
commit: null
---

## What was done

`channelflow.turning`: PRD §13A.11's forward path and its derivative roots,
§13A.12's stability gate, §13A.13's direct target and the experiment that ties
them together. 42 tests.

This closes REQ-WP-019's two remaining acceptance conditions and gives
REQ-NRT-F its first test. All twenty work packages are now `implemented`, and
the last of the six `REQ-NRT-*` constraints is off `draft`.

## Two guards over one property, again

The mutation sweep found a `path.py` mutation that survived: making the flat-path
branch of the solver return a spurious zero at `h = 0` changed no test. It could
not — `derivative_roots` discards anything at `h = 0`, because §13A.11 writes
`0 < h*`. The horizon filter was hiding a wrong answer from the solver
underneath it.

This is the fourth time in this repository (WP-010, WP-012, WP-020, and
REQ-ASSET-001 were the others), and the fix is the same each time: make the
inner property observable on its own. `slope_zeros` is public now, and a test
asserts that every zero it returns really zeroes the slope — over one path of
each degree, including the degenerate ones where a divide-by-zero would
otherwise live.

The second survivor was the rows-weighted aggregate. Every fold in the fixtures
happened to score the same number of rows, so an unweighted mean was
indistinguishable. Walk-forward folds are not the same size in practice, and the
small ones are the early ones — fitted on the least data. Now tested directly:
10 rows at 0.4 and 90 at 0.1 weight to 0.13, not 0.25.

## What was decided

- **The lattice is deterministic** ([[ADR-041]]), and a zero tolerance is
  refused: it perturbs nothing, so the presence rate is 1 by construction — a
  stability check that cannot fail.
- **`NO_EDGE` is returned, a caller error is raised** ([[ADR-042]]). Both have
  their own test; catching everything would look identical from one side.
- **`EDGE` needs both halves** — a promoted root *and* beating the base rate. A
  root that survives a stability gate and predicts nothing is not an edge.
- **The presence rate is the prediction's confidence.** A root that only some
  perturbed members found should predict weakly, and using the metric that
  already measures that is more honest than a constant.
- **A promotion refusal names every failing condition**, not the first. §13A.12
  lists eight so a rejection can say which held.

## Mutation results

Fifteen mutations, all caught, every restore verified and the tree swept
afterwards:

| Mutation | Caught by |
| --- | --- |
| The horizon bound on a root is dropped | `test_a_root_at_zero_is_not_a_candidate` (+1) |
| A plateau is classified as a turn | `test_an_inflection_is_not_a_turn` |
| Only the first root is returned | `test_both_roots_of_a_cubic_are_returned` |
| The flat-path branch invents a zero | `test_every_solved_zero_really_zeroes_the_slope` |
| A straight path reports a zero at `h = 0` | `test_every_solved_zero_really_zeroes_the_slope` |
| A zero tolerance is accepted | `test_a_negative_tolerance_is_refused` |
| The gate stops at the first failing condition | `test_every_failing_condition_is_named_not_just_the_first` |
| The presence-rate condition is dropped | `test_a_root_that_only_some_members_find_is_refused_by_name` |
| A missing feature becomes zero | `test_a_row_missing_a_declared_feature_is_refused` (+1) |
| Features follow the row's own order | `test_features_are_read_in_the_declared_order_not_the_dicts` |
| A constant-target fold is scored anyway | `test_a_fold_whose_target_never_occurs_is_reported_not_scored` |
| The aggregate is unweighted | `test_the_aggregate_is_weighted_by_rows_not_by_fold_count` |
| A promoted root needs no gate | `test_roots_that_no_gate_would_promote_are_reported_with_their_reasons` |
| The verdict ignores the baselines | `test_a_signal_free_experiment_returns_no_edge_and_raises_nothing` |
| A row with no forward path is skipped | `test_a_row_without_a_forward_path_is_refused` |

The last one is the quiet one: skipping unlabelled rows shrinks the evidence
without saying so, and a smaller sample is how a weak result becomes a
strong-looking one.

## What is still open

- **Three of §13A.12's eight conditions are deferred**, by name, in every
  decision: extrapolation bounds, data-quality state, walk-forward promotion
  gate.
- **`implemented` is not `verified`.** Nothing has run against a live venue. The
  criterion was that the experiment *can* return `NO_EDGE`, and it can; what it
  returns on real data is unknown.
- **BIAS-002 and BIAS-011 stay at `draft`** with their recorded reasons
  ([[ADR-024]]).
