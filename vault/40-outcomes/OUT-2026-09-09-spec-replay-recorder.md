---
id: OUT-2026-09-09-spec-replay-recorder
step: spec
records: [REQ-PIPE-001]
commit: null
---

## What was done

`specs/056-replay-recorder/spec.md`: three user stories, 11 functional
requirements, 11 success criteria.

## What was decided

- **A signal is written once, in its final state** (FR-004). The obvious
  implementation writes a row per bar, each a partial history of one signal, and
  nothing about those rows is malformed.
- **Observers cannot steer** (FR-006), checked by comparing a recorded run's
  report against an unrecorded one's rather than by inspecting the recorder.
- **A recording names only what it filled** (FR-008), because a dataset naming a
  table nobody wrote to would claim the run read it.

## What is still open

- Nothing from this step.
