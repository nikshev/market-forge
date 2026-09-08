---
id: OUT-2026-09-08-spec-turning-derivative
step: spec
records: [REQ-WP-019, REQ-NRT-F]
commit: null
---

## What was done

`specs/024-turning-derivative/spec.md`: four user stories, 15 functional
requirements, 10 success criteria. Two of the success criteria are REQ-WP-019's
own fourth and fifth acceptance conditions, quoted from the PRD.

## What was decided

- **The perturbation lattice is deterministic** ([[ADR-041]]). §13A.12 says
  "bootstrap/ensemble members"; a bootstrap needs a seed, and a stability metric
  that changes between runs cannot support the sentence "this root is stable".
- **`NO_EDGE` is a return value** ([[ADR-042]]). The criterion is about coupling:
  an experiment that signals its result by raising makes every caller stop for a
  hypothesis that did not pay off, which is a hypothesis's ordinary outcome.
- **A caller error still raises.** Otherwise a bug is reported as a fact about
  the market — an absence of edge in a hypothesis nobody actually tested.
- **§13A.12's conditions 2, 7 and 8 are deferred by name**, not assumed. They
  need subsystems outside this feature, and naming them in every decision is what
  keeps a partial gate from reading as a complete one.

## What is still open

- **No forecaster is chosen for production.** The experiment fits a path; whether
  that path is worth acting on is what it exists to answer.
