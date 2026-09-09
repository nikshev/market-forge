---
id: OUT-2026-09-09-requirement-experiment-registry
step: requirement
records: [REQ-REPRO-001, REQ-BIAS-011]
commit: null
---

## What was done

`REQ-REPRO-001`, hand-written from PRD §0 item 13, §41 rule 11, §29.B and §30.

## What was decided

- **One requirement covers both rules**, because they are enforced at the same
  place and neither is enforceable alone.
- **The scope names its exclusions**: reading the git commit, computing a model
  artifact's hash, PRD §30's PostgreSQL mirror, and automatic adoption by the
  seventeen research modules.
- **The commit and the dirty flag are data, not something the library reads.** A
  library that shells out to `git` cannot be tested and answers about whatever
  directory it is in.

## What is still open

- **Adoption.** Nothing walks the research modules and registers their runs;
  each adopts the registry as its own step, which is why [[REQ-BIAS-011]] stops
  at `specified`.
