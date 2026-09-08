---
id: OUT-2026-09-08-tasks-ofi-lob-features
step: tasks
records: [REQ-WP-011, REQ-PRIN-008]
commit: null
---

## What was done

14 tasks in six phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **Phase 1 is the registry, before any feature exists.** Ordering it first is
  what makes [[ADR-015]] a gate: a feature written after the registry has to
  fit it, a registry written after the features records whatever happened.
- **T011 names five mutations rather than "mutation-check the module".** The
  ones chosen are the guards whose removal leaves plausible numbers behind:
  OFI across a gap, a feature answering from an invalid book, a wall's whole
  decrease attributed to execution, a dropped registration, and a window
  boundary taken from ingest time.
- **The wall mutation is the one worth the effort.** ADR-014's split is an
  estimate; an estimate that quietly became "all executed" still produces
  believable output, and a pulled wall would read as absorbed demand — PRD
  §2.2's named failure mode.

## What is still open

- Nothing from this step.
