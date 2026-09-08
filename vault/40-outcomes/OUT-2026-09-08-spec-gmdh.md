---
id: OUT-2026-09-08-spec-gmdh
step: spec
records: [REQ-WP-018]
commit: null
---

## What was done

`specs/018-gmdh/spec.md`: four user stories, 13 functional requirements, 9
success criteria, two ADRs.

## What was decided

- **The external criterion takes an explicit second split** ([[ADR-030]]), and
  overlapping splits are refused before anything is fitted. This is GMDH's
  defining mechanism and its silent failure: a search scoring nodes on their
  own training rows grows layers as long as it is allowed to, because each
  layer can always fit the sample better.
- **Four of PRD §23.6's six baselines do not run, and every report says so**
  ([[ADR-029]]). Implementing tree ensembles well is a second project;
  implementing them badly is worse than not having them, because a GMDH model
  that beats a poor tree looks validated. Adding a dependency for them is a
  decision this work package should not make quietly.
- **The report scores Brier, not accuracy.** PRD §23.8 names it and Principle V
  requires calibration; accuracy would let a majority-class predictor look
  strong on an imbalanced target, which is exactly what the base-rate baseline
  exists to expose.
- **`Model.fit` raises for GMDH.** A single-split fit cannot be honestly
  provided, and inventing a split inside would choose a rule PRD §41 rules 1
  and 10 are specifically about.

## What is still open

- **§13A.11's derivative hypothesis and §13A.12's root filtering** are not
  built here; they belong to REQ-WP-019's ordering and carry REQ-NRT-F.
- **Nothing consumes the model.** It trains, scores and reports; the
  walk-forward promotion gate is separate work.
