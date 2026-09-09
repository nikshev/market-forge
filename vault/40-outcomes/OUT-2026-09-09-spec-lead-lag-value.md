---
id: OUT-2026-09-09-spec-lead-lag-value
step: spec
records: [REQ-EXP-010]
commit: null
---

## What was done

`specs/043-lead-lag-value/spec.md`: three user stories, 12 functional
requirements, 11 success criteria.

## What was decided

- **A declared threshold grid**, not a continuous optimizer: five values a
  reader can see and disagree with.
- **The latency is required**, because "realistic" is a claim about somebody's
  infrastructure.
- **The signals are supplied.** [[REQ-WP-016]] computes the basis and says
  nothing about direction.
- **The exit rule is fixed and symmetric**, because the question is about
  direction rather than exits.

## What is still open

- **Sub-bar latency** needs the tick replay PRD §40 mentions.
