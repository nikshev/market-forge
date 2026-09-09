---
id: OUT-2026-09-09-spec-dex-incremental
step: spec
records: [REQ-EXP-007]
commit: null
---

## What was done

`specs/040-dex-incremental/spec.md`: three user stories, 9 functional
requirements, 8 success criteria.

## What was decided

- **The not-run state is asserted, not assumed.** A test pins which families are
  empty, so registering them later is a deliberate change rather than a silent
  one.
- **The instrument is required.** A DEX result is about a pool.
- **The machinery is shared with [[REQ-EXP-004]]**, so both experiments'
  increments mean the same thing.

## What is still open

- **The DEX features are unregistered.** That is what four of the five arms are
  waiting on.
