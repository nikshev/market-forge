---
id: OUT-2026-09-10-plan-research-run
step: plan
records: [REQ-WP-024]
commit: null
---

## What was done

`specs/063-research-run/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/study.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-024]] moves to `planned`.

## What was decided

- **The comparison reports what it fitted.** Refitting to obtain a hash is a
  second scoring path, and a comparison is only honest if one code path produced
  both numbers.
- **One artifact per variant per fold.** A variant appearing twice in one fold —
  as the subject and as a baseline of the same name — was fitted identically both
  times; counting it twice gives it a longer artifact than its rivals for no
  reason a reader could recover.
- **The winner must beat the base rate.** A model that cannot is not a model.
  `None` otherwise, which is a promotion that did not happen rather than a field
  with no best member.
- **Registration precedes citation, and the artifact check follows the gate.**
  The gate refuses a winner whose field is not on record; a caller fixing a
  dirty tree should not have to fix an artifact complaint to discover it.
- **The shared fixtures moved up to `tests/unit/conftest.py`.** Copying them
  would be two fixtures that drift, and a study asserting against a copy of a
  dataset the turning tests no longer use is a test asserting about its own
  fixture.

## What is still open

- **`report_comparison` had to change**, and that is recorded as a finding in the
  implement note rather than absorbed.
