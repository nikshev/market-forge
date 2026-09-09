---
id: OUT-2026-09-09-spec-volume-confluence
step: spec
records: [REQ-EXP-005]
commit: null
---

## What was done

`specs/038-volume-confluence/spec.md`: three user stories, 11 functional
requirements, 10 success criteria.

## What was decided

- **The effect size has no default**, and a test reads the signature to say so.
- **Three verdicts**, the third of which is what most confluence claims deserve.
- **Timeouts are counted and are not decisions.**
- **Two populations, not four.** A boundary on both an edge and a node is
  confluent once; splitting by kind is a finer question than EXP-005 asks.

## What is still open

- **Nothing runs it on real setups.** The study takes observations; producing
  them for a real venue is pipeline work.
