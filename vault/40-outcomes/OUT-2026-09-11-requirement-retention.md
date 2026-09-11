---
id: OUT-2026-09-11-requirement-retention
step: requirement
records: [REQ-WP-038]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-038.md`, from PRD §6.4.9 and §45's Phase 8.
One of [[REQ-PHASE-8]]'s five open deliverables.

## What was decided

- **The PRD's own refusal to name durations is the first acceptance line.**
  "Suggested semantics, not hard-coded durations" is unusually explicit, and it
  means a default written into this code would contradict the section it
  implements.
- **Tier D is where retention stops being about age.** A snapshot an
  experiment's lineage names must survive however old it is. A retention pass
  that expired one would destroy §0 item 13's reproducibility *silently*: the
  model still loads, the config still reads, and the run simply stops being
  checkable.
- **The pruning order is the inverse of the writing order**, which follows from
  [[REQ-WP-037]]'s argument rather than repeating it. Data before manifest when
  writing; manifest before data when removing. Any other order leaves the
  corruption `table.py` refuses to create.
- **The newest snapshot is never expired**, whatever the policy says. A table
  with no readable current state is not a retained table; it is a deleted one
  with extra steps.
- **Deleting is a capability, not an operation.** `ObjectStore` deliberately has
  no `delete` and the table layer must never have one. Adding it to the shared
  port to serve retention would hand the commit path a gun it has no use for.

## What this requirement found

**`Registration` does not record which dataset snapshot a model was trained
on.** PRD §0 item 13 asks a result to be reproducible from "a versioned dataset
+ config + code commit hash + model artifact hash"; the registry holds the last
three and not the first. Nothing has needed it until now, and retention is
exactly where its absence bites — there is no lineage to read, so nothing can be
pinned automatically.

Named rather than designed around: retention takes pinned snapshots as an
argument, and the day something records lineage it reads that instead. Worth its
own requirement later.

## What is still open

- **Tiers A and C have no store.** Pinot is deferred by [[ADR-002]] and nothing
  writes a raw archive. Not deferred work hiding here — there is nothing to
  retain.
- **Nothing schedules a retention pass**, as nothing schedules a backup.
- **The lineage gap above**, which is the most useful thing this extraction
  produced.
