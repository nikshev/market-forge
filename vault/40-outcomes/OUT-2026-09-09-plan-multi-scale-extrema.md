---
id: OUT-2026-09-09-plan-multi-scale-extrema
step: plan
records: [REQ-EXP-016]
commit: null
---

## What was done

One module, three predicates, one pricing function. 9 tasks.

## What was decided

- **The rules are predicates and the pricing is shared.** A rule carrying its
  own scoring would let two rules' numbers stop meaning the same thing.
- **A candidate without context is excluded from every arm.** Scoring it in the
  base and not in the filtered arm would make the warm-up look like the rule's
  contribution.
- **`available_frame` is public**, because the closing guard is the property
  this module rests on and it has to be testable on its own.

## What is still open

- Nothing from this step.
