---
id: OUT-2026-09-11-implement-iceberg-callers
step: implement
records: [REQ-WP-039]
commit: null
---

## What was done

Step two: every caller moved from the hand-rolled table to the Iceberg one.
Eleven source files — the five domain table adapters, the API's lakehouse
repository, both pipeline entry points, and both registries — and thirteen test
files. `ObjectStore` became `Catalog`, `Table` became `IcebergTable`, and a
`catalog` fixture in a new root `tests/conftest.py` gives every suite a SQLite
catalog in a temporary directory.

Full suite green: 1777 passing, no services needed.

[[REQ-WP-039]] stays `planned`. The hand-rolled format is still here, with its
own tests; deleting it is step three.

## What this step found

**Iceberg's scan returns rows newest-commit-first. The plane it replaces
returned them oldest-first.** Measured after a repository test failed:

    four appends of 0, 1, 2, 3  ->  scan gives [3, 2, 1, 0]

Nothing announces this. Reversed rows are still rows, every type is right, every
count is right. What breaks is every "latest row wins" reader — `markets()`
folds rows in order and would have started returning the *oldest* description of
each instrument, and `read_bars` promises PRD §29.4's order and would have
returned it backwards.

No test anywhere asserted the order, in either implementation. It was a
guarantee the whole API leaned on and nobody had written down, which is exactly
the shape the spec warned about: a migration fails by arriving with a working
table that quietly stopped doing one of the things the old one did.

`read` now reconstructs the order from the snapshot chain — oldest snapshot
first, each file taken the first time a snapshot names it — rather than trusting
the scan. Two tests now assert it, and four mutants over the ordering are caught.

## The mistake I made, and what it cost

A blanket rename of `store` to `catalog` **merged two independent planes into
one** in two tests. Both tests exist precisely because the planes are separate:
one replays the same bars twice and compares, the other checks that an artifact
does not resolve against a registry that never recorded it. Sharing a catalog
made the first skip everything on the second pass — the watermark working
correctly — and the second resolve for the most boring possible reason.

Both now build a second catalog of their own, with a comment saying why. The
lesson is about mechanical renames across a test suite: the ones that break
loudly are cheap, and the ones that turn a test into a tautology are not.

## Smaller things

- **The decimal conversion came back.** `_for_arrow` turns a `Decimal` into its
  exact string, and the first version of `IcebergTable._arrow` skipped it. Its
  inverse is new: the content hash is computed from rows read back, and the
  canonical encoder expects domain shapes. Hashing storage shapes would have
  worked and put a second canonicalisation in the codebase, and two canonical
  forms drift.
- **`_in_memory` in the repository conformance test takes a catalog it ignores**,
  so both factories have one shape. The alternative was a special case in the
  fixture for the implementation that needs nothing.

## What is still open

- **`table.py` and its 110 tests are still here**, along with `backup.py`, which
  is written against its layout. Step three.
- **[[REQ-WP-037]]'s backup and restore** need their Iceberg equivalent.
- **Where the catalog lives on the stack**, and who creates the namespace: no
  production wiring exists yet, so nothing constructs a PostgreSQL catalog.
- **Reading costs one plan per snapshot.** Acceptable now and worth revisiting
  when a table has thousands.
