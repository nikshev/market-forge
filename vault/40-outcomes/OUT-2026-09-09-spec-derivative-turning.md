---
id: OUT-2026-09-09-spec-derivative-turning
step: spec
records: [REQ-EXP-012]
commit: null
---

## What was done

`specs/045-derivative-turning/spec.md`: three user stories, 11 functional
requirements, 12 success criteria.

## What was decided

- **The centred filter makes the labels and is refused as a candidate**, and the
  refusal comes from the production causality guard rather than a local check.
- **The report says both halves of what its labels are**: a centred filter, and
  one that cannot run live.
- **A local polynomial is read at the right edge of its window**, which is the
  whole difference between a causal estimator and a forbidden one.
- **Precision over no calls is absent, not zero.**

## What is still open

- **The Savitzky-Golay-equivalent variant is not implemented.** EXP-012 lists it
  "if retained"; its one-sided form is the causal local polynomial already here,
  and its centred form is a label maker. Recorded as an assumption in the spec
  rather than a gap.
