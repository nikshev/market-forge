---
id: OUT-2026-09-09-plan-gmdh-extrema
step: plan
records: [REQ-EXP-013]
commit: null
---

## What was done

One module, one refactor. 9 tasks.

## What was decided

- **`read_derivative_folds` is extracted from `run_derivative_experiment`.** The
  function was doing two jobs: reading every validation row's forward path, and
  ruling on what the readings were worth. EXP-013 needs the first and asks a
  different question of the second, and a second copy of the loop would be a
  second promotion gate that only looked like the first.
- **Every arm supplies its own probabilities to the same `compare` call**, so
  the four are scored on identical rows in identical order.
- **The promotion gate is unchanged.** This experiment decides how many roots go
  into one average, not what makes one root acceptable.

## What is still open

- Nothing from this step.
