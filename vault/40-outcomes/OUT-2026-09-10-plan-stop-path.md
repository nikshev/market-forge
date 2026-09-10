---
id: OUT-2026-09-10-plan-stop-path
step: plan
records: [REQ-WP-032]
commit: null
---

## What was done

`specs/070-stop-path/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/view.md`, `quickstart.md`. [[REQ-WP-032]] moves to `planned`.

## What was decided

- **The module has no `bars` parameter, and that is the design.** A function
  with no price series cannot produce a price-derived trail, and anyone who
  wants one has to add a parameter — visible in a diff. The alternative, a
  golden-path test, passes for a recomputation that agrees today and keeps
  passing when the anchor logic moves underneath it.
- **An anchor the proposal could not have known refuses the whole view.** That
  is the corrupted case, not the absent one. Dropping the anchor renders a
  clean chart from a wrong path; drawing it renders the forbidden chart. Both
  leave the reader nowhere to notice, so the answer is `inconsistent` with the
  offending proposal named.
- **`lockedProfitR` is a number and `mfeR`/`maeR` are nullable.** A stop still
  below entry locks nothing — zero is the true reading. An excursion over
  nothing observed is not zero. The same distinction the last requirement spent
  itself on, pointed the other way for once.

## The spec defect this step caught

**FR-009 was wrong**, and is corrected in `spec.md` rather than implemented as
written. It required risk *and* excursion to be refused over an empty path.
Excursion needs a path — MFE and MAE are of something observed. Open risk does
not: it is the position's own current stop against its own entry over its own
accepted initial risk, all three of which exist whether or not the policy ever
ran. Refusing it would have taught a reader that an unrun policy means unknown
risk, which is the reverse of true.

Worth naming because it is the failure this requirement is about, committed in
the requirement's own spec: treating an absent computation as an absent fact.

## What is still open

- Nothing new. The three from [[OUT-2026-09-10-spec-stop-path]] stand: nothing
  stores proposals, trail aggressiveness and data-health have no producer, and
  where the "why not tighter" grouping belongs is unsettled.
