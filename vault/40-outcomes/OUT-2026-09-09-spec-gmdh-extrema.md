---
id: OUT-2026-09-09-spec-gmdh-extrema
step: spec
records: [REQ-EXP-013]
commit: null
---

## What was done

`specs/046-gmdh-extrema/spec.md`: three user stories, 14 functional
requirements, 15 success criteria.

## What was decided

- **Two of the seven metrics are absent for the classifier arms**, on purpose.
  A classifier never names a time or a price, and that blank is what the
  derivative route's complexity is weighed against.
- **The stability figures are averaged over the rows that produced a root**, and
  both counts are reported ([[ADR-051]]).
- **The verdict names every failure**, not the first.
- **The truth is the label-side forward path** — where it turns is when the turn
  came, PRD §24.2's permission.

## What is still open

- **The call threshold is a required argument with no default.** It decides
  which rows each arm is judged on and every economic figure moves with it;
  PRD §13A.27's warning applies and nothing here validates a value.
