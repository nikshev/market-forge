---
id: OUT-2026-09-09-spec-defi-confluence
step: spec
records: [REQ-EXP-015]
commit: null
---

## What was done

`specs/048-defi-confluence/spec.md`: three user stories, 13 functional
requirements, 13 success criteria.

## What was decided

- **"Strict" becomes a refusal.** An arm two families from both references is
  named and rejected rather than scored, because its delta would be the sum of
  two contributions under one family's name.
- **Every family is read in both directions**, added alone and removed from the
  full set. They disagree whenever families overlap.
- **The fold fingerprint carries the spans**, not just the count — two studies
  over different rows can both use three folds.
- **The instruments are named and checked against the data.**

## What is still open

- **None of EXP-015's DEX families has a registered producer yet.** The prefixes
  are declared and resolve to nothing; the tests supply the mapping explicitly,
  which is why they measure the ablation rather than that absence.
