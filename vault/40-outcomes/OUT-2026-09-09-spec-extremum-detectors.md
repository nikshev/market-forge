---
id: OUT-2026-09-09-spec-extremum-detectors
step: spec
records: [REQ-EXP-011]
commit: null
---

## What was done

`specs/044-extremum-detectors/spec.md`: three user stories, 12 functional
requirements, 12 success criteria.

## What was decided

- **Nothing is ranked**, and the report says why.
- **The channel width is passed in**, not fitted by the detector.
- **Regimes are split at the series' own median.**
- **A method with no channel model is unavailable**, not one that found nothing.

## What is still open

- **The detector is unchanged otherwise**, and this experiment does not select
  a mode for production.
