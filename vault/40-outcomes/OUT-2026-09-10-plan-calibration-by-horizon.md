---
id: OUT-2026-09-10-plan-calibration-by-horizon
step: plan
records: [REQ-WP-023]
commit: null
---

## What was done

`specs/062-calibration-by-horizon/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/reporter.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-023]] moves to `planned`.

## What was decided

- **Exact horizons, not buckets.** Bands would add a second arbitrary choice on
  top of the minimum, and two arbitrary choices interact: a finding could appear
  or vanish depending on where a band edge fell, which is a result nobody can
  argue with.
- **Thinness is counted in rows, never in positive outcomes.** A target that
  never occurs at a horizon has observations and no positives — a real
  calibration, usually a bad one, and exactly the finding worth surfacing. Keying
  on positives would hide it, which is this requirement's own failure mode one
  level down.
- **The row shape arrives as a Protocol.** `dataset.leakage` already does this
  with `RowLike`; importing the dataset package into metrics would run the
  dependency backwards for two fields.

## What is still open

- **A labeller that varied `H` per row would produce one slice per row** and a
  report that says nothing. Nothing does that today, and the failure would be
  visible rather than silent — but nothing warns about it either.
