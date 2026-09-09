---
id: OUT-2026-09-09-spec-canonical-data-plane
step: spec
records: [REQ-STORE-001]
commit: null
---

## What was done

`specs/052-canonical-data-plane/spec.md`: three user stories, 16 functional
requirements, 15 success criteria.

## What was decided

- **A requirement about what a hash must not cover.** FR-006 forbids hashing the
  Parquet bytes. The obvious implementation passes every other requirement here
  and fails PRD §0 item 13 on a schedule nobody controls — the next `pyarrow`
  release.
- **A backend that cannot promise a conditional write is refused**, not
  emulated. The emulation compiles, passes a single-writer suite, and loses
  races silently.
- **The isolation rule is a success criterion**, not a convention: no domain
  package may import this one or a storage backend.

## What is still open

- **Nothing here specifies a table.** The plane and its tables are different
  pieces of work, and conflating them would have made this specification a
  survey of §29.B's seventeen schemas instead.
