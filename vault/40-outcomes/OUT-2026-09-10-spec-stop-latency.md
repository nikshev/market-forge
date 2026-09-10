---
id: OUT-2026-09-10-spec-stop-latency
step: spec
records: [REQ-WP-033]
commit: null
---

## What was done

`specs/071-stop-latency/spec.md`: three user stories, 9 functional requirements,
6 success criteria. [[REQ-WP-033]] moves to `specified`.

## What was decided

- **FR-008 is made checkable by SC-004.** "Never chosen by whichever ordering
  pays better" is a statement about motive, and no test reads motive. Two paths
  on which the tie rule pays in opposite directions, required to resolve the
  same way, is the checkable form: an implementation choosing by outcome fails,
  one that merely happens to be conservative passes. That is the right standard.
- **SC-002 is the regression floor.** Zero latency must reproduce the prior
  outcomes field for field, which turns the whole change into a diff against a
  known state rather than a set of new numbers nobody can check.
- **The default is the PRD's own 160 ms**, attributed to the leg its example
  actually measures — computed to acknowledgement — with the decision and
  computation legs stated as zero because the PRD gives no figure for them. The
  total is therefore a floor and says so. Guessing the other two would have put
  an invented number where an honest floor belongs.
- **Baselines run under the same latency.** A naive policy obeyed instantly
  while the adaptive one waits is not a comparison of policies, and the report
  would look exactly as it does now.

## The rule this spec could not honour as written

**§44A.27's trigger-versus-target ordering cannot arise in this model.** A
`PricePoint` carries one price, so within a point there is no ordering to
choose. Rather than assert the rule with a test over a case the model cannot
produce — which would read as coverage and be empty — the spec honours it where
this feature genuinely creates an ordering question: the touch that lands
exactly at the acknowledgement instant. That tie is resolved by one predeclared
conservative rule, stated where it is applied.

The requirement's acceptance line therefore stands unmet in its intra-bar form,
and is recorded here as such rather than quietly counted.

## What is still open

- **Whether decision and computation latency should ever default to non-zero.**
  Both are real and unmeasured.
- **Whether an ambiguous outcome should be excludable from a comparison**
  instead of resolved conservatively.
- **Intra-bar ordering**, as above: it needs an OHLC path model, which is a
  larger change than this requirement.
