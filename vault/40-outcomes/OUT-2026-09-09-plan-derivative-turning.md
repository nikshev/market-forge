---
id: OUT-2026-09-09-plan-derivative-turning
step: plan
records: [REQ-EXP-012]
commit: null
---

## What was done

One module, one Protocol correction. 7 tasks.

## What was decided

- **The labeller is an object that declares itself centred**, not a private
  function with a warning in its docstring. `require_causal` reads declarations.
- **The guard runs on every candidate before the comparison starts**, not inside
  the scoring loop where a silent skip would be invisible.
- **The tolerance is a named research default**, because it decides what "found
  it" means and PRD §13A.27's warning applies to it.

## What is still open

- Nothing from this step.
