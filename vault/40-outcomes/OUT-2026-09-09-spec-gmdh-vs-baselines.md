---
id: OUT-2026-09-09-spec-gmdh-vs-baselines
step: spec
records: [REQ-EXP-008]
commit: null
---

## What was done

`specs/041-gmdh-vs-baselines/spec.md`: two user stories, 13 functional
requirements, 11 success criteria.

## What was decided

- **Build the two baselines rather than record them as unmet.** EXP-008's
  acceptance names them, and the experiment is what decides whether GMDH is worth
  keeping.
- **Answer [[ADR-029]] on its own terms** ([[ADR-050]]): required strengths, and
  a tree deep enough to see an interaction.
- **PR-AUC, not ROC-AUC.**
- **The metrics live with the models**, because [[REQ-EXP-013]] needs them too.

## What is still open

- **Two baselines still not run**: the single tree, and the LightGBM dependency
  question ADR-029 left open on purpose.
