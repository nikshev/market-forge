---
id: OUT-2026-09-10-fix-validation-regime
step: implement
records: [REQ-WP-022, REQ-WP-024]
commit: null
---

## What was done

`Registration` gains `validation_regime` and enforces non-overlap only for a
single split. `run_study` writes the folds' true extents instead of `1/2/2/3`.
[[ADR-058]] carries the decision.

Six new tests, 1593 in the suite, mypy clean.

## What this corrects

A defect I introduced and then documented as a limitation. The registration's
non-overlap rule was mine, justified with a PRD citation that does not support
it: §23.9 asks for four spans and says nothing about their order, and §41 rule 10
is about a locked test segment which walk-forward satisfies per fold.

Because a walk-forward run cannot satisfy the rule, the first real registrations
wrote invented numbers into four fields and the outcome note called it "shape
rather than truth". That is a registry — whose only job is describing an artifact
truthfully — carrying four lies, and it passed a mutation sweep and a green CI.

## What was decided

- **The rule applies to a single split and nothing else.** For one split the
  spans are the whole of what happened, so an overlap is the leak. Across
  walk-forward folds the outer extents overlap because of the schedule, not
  because of leakage.
- **The guarantee did not move to a weaker place.** It was always in
  `WalkForwardFolds` and `certify`; the registration was restating it with a
  cruder test that a correct scheme legitimately fails.
- **`validation_regime` has no default** ([[ADR-015]]): it decides which rule
  applies, so an author must say.
- **The test asserts the overlap** rather than tolerating it, so the next person
  who wants to tighten the rule sees why it is loose.

## What is still open

- **Nothing checks that a registration's spans are true**, only that they are
  accepted — which is exactly how the invented ones survived. A check would have
  to compare a registration against the dataset it claims to describe, and the
  registry holds no reference to one.
- **`single_split` has no producer.** Nothing in the repository trains on one
  split today, so that branch of the rule is exercised only by tests.
