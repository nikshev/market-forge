---
id: OUT-2026-09-09-spec-lookback-sensitivity
step: spec
records: [REQ-EXP-002]
commit: null
---

## What was done

`specs/035-lookback-sensitivity/spec.md`: three user stories, 12 functional
requirements, 10 success criteria.

## What was decided

- **The rule becomes structure.** `recommend` returns nothing when there is no
  plateau, rather than falling back to the peak.
- **An absent value breaks a plateau** rather than being skipped.
- **Adjacency is by position in the list**, not numeric distance: 150 and 200 are
  neighbours in EXP-002's sweep though fifty bars apart, and that is the
  resolution the experiment chose.
- **The metric is expectancy after costs.** The rule is about how it is used, not
  about replacing it.

## What is still open

- Nothing from this step.
