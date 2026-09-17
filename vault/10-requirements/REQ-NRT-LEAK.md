---
id: REQ-NRT-LEAK
title: Every feature gives the same value on a truncated and a full dataset
type: constraint
prd_ref: "§35.4"
prd_lines: "4879-4887"
phase: null
status: implemented
depends_on: [REQ-WP-019]
tags: []
hard_gated: true
---

## Requirement

PRD §35.4, quoted in full:

> **For every feature:**
>
> 1. Run on truncated dataset through `t`.
> 2. Run on full dataset but ask for feature at `t`.
> 3. Values must match exactly within numeric tolerance.
>
> This should be an automated CI suite.

The last line is a requirement, not an aside. "For every feature" is only true if
something enumerates them; a suite that checks the features somebody remembered
is a suite that grows a hole every time a feature is added.

**The token is a word, not a letter**, for the reason [[REQ-NRT-REPAINT]] gives:
`A`–`F` are §13A.28's own names, and this is §35.4.

### 55 features promise this, and nothing checks

`FeatureSpec` carries `point_in_time_safe: Literal[True]`. The type makes any
other value unregisterable, so **all 55 registered features declare that they are
point-in-time safe** — and the only test that touches the field asserts it is a
`bool`, which `Literal[True]` guarantees before the test runs. The declaration is
a promise the type extracts and nobody verifies. §35.4 is its verification.

### The surface this has to cover

Measured: **55** specifications, one per exposed name, across eight producing
modules and seven families — `derivatives` 19, `order_book` 15, `trade_flow` 5,
`order_flow` 5, `volume_structure` 5, `channel` 4, `defi` 2.

*(An earlier draft of this note said 27. That was the registry after importing
only `channelflow.features.*`; three more packages register features, and
`exposed_feature_names()` is the canonical enumeration because it imports all
eight. Corrected here rather than quietly — the number is the scope.)*

`tests/unit/dataset/test_leakage.py` checks *dataset rows* — that a feature's
`available_at` is not after `t`, that a label is not knowable at `t`. That is a
check on assembled data. §35.4 is a check on the **computation**: run it twice
over different amounts of input and demand the same answer. A feature whose
implementation peeks at a later row produces rows that pass the first check and
values that fail this one.

Constitution Principle I is the same rule stated as a prohibition, and it is
never waived. This is the mechanical test of it.

**The registry holds no callable.** A `FeatureSpec` is metadata plus
`test_fixture`, a string naming the test that pins the arithmetic. So the
registry can say *which* features must have a truncation case; it cannot produce
one. Each case therefore supplies its own callable and its own input, and the
enumeration's job is the set difference: a registered name with no case is a
failure that names the feature.

## Acceptance

- Every specification in the feature registry participates, enumerated from the
  registry rather than listed by hand.
- A feature present in the registry with no truncation case fails the suite,
  naming the feature. Adding a feature without one is red, not quiet.
- For each: computing at `t` from input truncated at `t`, and computing at `t`
  from the full input, give equal values. Equality is exact for integers and
  within a stated tolerance for floating point, with the tolerance written down
  rather than tuned until the suite passes.
- A feature that cannot be evaluated this way is **refused rather than skipped**,
  with the reason recorded where the enumeration can see it. A skip that reports
  green is the failure mode this requirement exists to prevent.
- A deliberately leaking feature is caught and named, proven by introducing one.
- It runs in CI with no services and no network.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-114-repaint-and-leak-suites]]
- **Tests:**
    - `tests/unit/features/test_truncation_parity.py::test_a_case_for_an_unregistered_feature_is_refused`
    - `tests/unit/features/test_truncation_parity.py::test_a_difference_inside_the_tolerance_is_not_a_divergence`
    - `tests/unit/features/test_truncation_parity.py::test_a_difference_outside_the_tolerance_is_a_divergence`
    - `tests/unit/features/test_truncation_parity.py::test_a_leaking_feature_is_caught_and_names_both_values`
    - `tests/unit/features/test_truncation_parity.py::test_a_refusal_covers_the_feature_it_names`
    - `tests/unit/features/test_truncation_parity.py::test_a_refusal_has_to_give_a_reason[   ]`
    - `tests/unit/features/test_truncation_parity.py::test_a_refusal_has_to_give_a_reason[\n  ]`
    - `tests/unit/features/test_truncation_parity.py::test_a_refusal_has_to_give_a_reason[\t]`
    - `tests/unit/features/test_truncation_parity.py::test_a_refusal_has_to_give_a_reason[]`
    - `tests/unit/features/test_truncation_parity.py::test_a_wall_ignores_trades_from_after_its_moment`
    - `tests/unit/features/test_truncation_parity.py::test_an_integer_and_an_equal_float_are_different_answers`
    - `tests/unit/features/test_truncation_parity.py::test_every_case_computes_a_value`
    - `tests/unit/features/test_truncation_parity.py::test_every_registered_feature_is_covered_or_declared_outstanding`
    - `tests/unit/features/test_truncation_parity.py::test_integers_and_none_compare_exactly`
    - `tests/unit/features/test_truncation_parity.py::test_the_debt_register_is_what_stops_this_requirement_completing`
    - `tests/unit/features/test_truncation_parity.py::test_the_inputs_are_not_degenerate`
    - `tests/unit/features/test_truncation_parity.py::test_the_registry_is_fully_imported_before_anything_is_counted`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[basis_bps]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[channel_position]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[channel_quality_score]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[channel_slope_normalized]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[channel_width_pct]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[cvd]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[cvd_acceleration]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[cvd_slope]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[delta_notional]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[funding_acceleration]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[funding_rate_settled]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[funding_z]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[liquidation_imbalance_5m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[liquidation_intensity_5m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[liquidation_long_usd_5m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[liquidation_short_usd_5m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[long_short_ratio]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[long_short_z]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[mark_premium_bps]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[normalized_delta]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[ofi_1m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[ofi_1s]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[ofi_30s]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[ofi_5s]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[ofi_bar]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[oi_change_1h]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[oi_change_5m]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[oi_to_volume]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[oi_z]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[open_interest_usd]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[price_oi_regime]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[time_since_liquidation_spike]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[top_trader_long_short_ratio]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[wall_cancelled_size_est]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[wall_executed_size_est]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[wall_persistence_ns]`
    - `tests/unit/features/test_truncation_parity.py::test_the_truncated_and_full_runs_agree[wall_refill_count]`
    - `tests/unit/features/test_truncation_parity.py::test_two_large_integers_one_apart_are_not_the_same_answer`
- **Code:**
    - `src/channelflow/features/truncation.py`
    - `src/channelflow/features/walls.py`
- **Outcomes:** [[OUT-2026-09-15-implement-truncation-channel-family]], [[OUT-2026-09-15-implement-truncation-derivatives]], [[OUT-2026-09-15-implement-truncation-flow-families]], [[OUT-2026-09-15-implement-truncation-order-book]], [[OUT-2026-09-15-spec-repaint-and-leak-suites]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
