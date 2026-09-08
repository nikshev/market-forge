---
id: OUT-2026-09-08-tasks-pit-dataset
step: tasks
records: [REQ-WP-017]
commit: null
---

## What was done

15 tasks in six phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **T012's third mutation is the one to watch.** Labelling from `extremum_time`
  rather than `known_at` produces a dataset that trains beautifully: the label
  is available before the market could have known it, and every metric computed
  on it looks like an edge. It is the exact defect PRD §41 rule 3 names, and it
  would survive any amount of eyeballing.
- **T014 leaves five BIAS notes at `draft` deliberately**, per [[ADR-024]].
  Advancing them would be the easiest thing in this feature to do by accident,
  since they are adjacent in the same directory.

## What is still open

- Nothing from this step.
