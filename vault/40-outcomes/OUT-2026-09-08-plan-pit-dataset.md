---
id: OUT-2026-09-08-plan-pit-dataset
step: plan
records: [REQ-WP-017]
commit: null
---

## What was done

Five modules under `src/channelflow/dataset/`, five test files, 15 tasks in six
phases.

## What was decided

- **`leakage.py` is separate from the modules it checks.** A checker living
  inside the thing it checks tends to be written to pass: it sees the same
  intermediate state, and the temptation is to assert on that rather than on
  the output. It takes a built dataset and knows nothing else.
- **Every refusal is a named exception, not a `None`.** The join has five ways
  to decline a row, and a caller getting `None` five times cannot tell a
  missing snapshot from a leaking one.
- **Folds are built from label horizons, not row counts.** The purge exists
  because a label at `t` describes what happened until `t + H`; a boundary
  drawn without `H` in hand cannot know which training rows reach across it.
- **The locked test split is a method that raises**, not a flag someone reads
  and ignores. Asking for it during tuning is an error carrying PRD §41 rule
  10 in its message.

## What was rejected

- **A single `build()` returning rows and swallowing the rest.** The counts of
  what was dropped, and why, are the difference between "no setups" and "the
  filter was inverted".

## R5 will fire again if the BIAS notes are moved to `planned`

The six are `hard_gated`. They stay at `specified` until their tests exist,
then go straight to `implemented` — `/sdd-plan` step 4, and the lesson
REQ-WP-019 learned in this same step.

## What is still open

- Nothing from this step.
