---
id: REQ-NRT-LEAK
title: Every feature gives the same value on a truncated and a full dataset
type: constraint
prd_ref: "§35.4"
prd_lines: "4879-4887"
phase: null
status: specified
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

### The surface this has to cover

Measured: `channelflow.features.REGISTRY` holds **27** specifications once the
feature modules are imported, and they expose **55** names between them
(`exposed_feature_names()`), with no exposed name lacking a registration.

`tests/unit/dataset/test_leakage.py` checks *dataset rows* — that a feature's
`available_at` is not after `t`, that a label is not knowable at `t`. That is a
check on assembled data. §35.4 is a check on the **computation**: run it twice
over different amounts of input and demand the same answer. A feature whose
implementation peeks at a later row produces rows that pass the first check and
values that fail this one.

Constitution Principle I is the same rule stated as a prohibition, and it is
never waived. This is the mechanical test of it.

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
- **Outcomes:** [[OUT-2026-09-15-spec-repaint-and-leak-suites]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
