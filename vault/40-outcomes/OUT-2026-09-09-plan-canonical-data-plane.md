---
id: OUT-2026-09-09-plan-canonical-data-plane
step: plan
records: [REQ-STORE-001]
commit: null
---

## What was done

Five modules, two new dependencies. 11 tasks.

## What was decided

- **No current-snapshot pointer.** The newest snapshot is the highest manifest
  version present. A pointer needs its own atomicity and is one more thing that
  can disagree with the manifests it points at.
- **Data files are written before the manifest that names them.** A lost race
  leaves an orphan, which is garbage rather than corruption; the other order
  produces a manifest naming files that may never arrive.
- **The research extract goes through the port**, not through an `s3://` glob. A
  glob reads whatever is under a prefix at that moment, orphans included — a
  different question with the same shape.
- **`pyarrow` and `duckdb` get mypy import overrides rather than hand-written
  stubs.** Stubs for two large C++ bindings would be a second source of truth
  about someone else's API; strict mode still checks every signature here that
  touches them.

## What is still open

- **A snapshot's manifest lists every file in the table, including its parent's.**
  That is how Iceberg works too, and it means a manifest grows linearly with the
  number of commits. Compaction and manifest lists are the answer when it
  matters, and nothing needs them yet.
