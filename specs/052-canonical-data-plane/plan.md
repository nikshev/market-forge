# Implementation Plan: Canonical Parquet data plane

**Branch**: `store-001-lakehouse` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Five modules under `channelflow.lakehouse`: a four-operation object-store port,
a typed schema with a fingerprint, an immutable snapshot with a content hash, a
table that commits atomically over the port, and DuckDB access to one snapshot's
extract.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**New dependencies**: `pyarrow` (Parquet) and `duckdb` (research extracts). Both
libraries; neither is a service, which is why [[ADR-002]]'s stack still has two
containers.

**Testing**: 80 unit tests against a store double, 4 integration tests against
MinIO.

**Target Platform**: `src/channelflow/lakehouse/`.

**Constraints**: FR-003 (atomicity), FR-006 (identity, [[ADR-053]]), FR-015
(PRD §29.0's isolation rule).

**Scale/Scope**: 5 modules, 84 tests, 25 mutations.

## Constitution Check

- **I (no look-ahead, ever)** — the point-in-time read is this rule at the
  boundary where data leaves storage.
- **V (finalized snapshots are not rewritten)** — a manifest is written once
  under a key naming its own version. Here it is a property of the key space
  rather than a discipline.
- **VII (live and replay are the same code)** — one object-store port, one I/O
  path; the research extract goes through it rather than around it.
- **X (thresholds are configuration)** — nothing here has a threshold.
- **XI (results are reproducible)** — [[ADR-053]] is this principle applied to a
  dataset's name.
- **XIV** — traces to REQ-STORE-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/lakehouse/store.py       # the port, S3, and a test double
src/channelflow/lakehouse/schema.py      # typed columns, fingerprint, row encoding
src/channelflow/lakehouse/snapshot.py    # files, identity, manifest serialization
src/channelflow/lakehouse/table.py       # the chain, and the atomic commit
src/channelflow/lakehouse/research.py    # bounded DuckDB extracts
```

**Structure Decision**: the table layer depends on a port with four operations
and no query language. That is what makes PRD §29.0's substitution — ClickHouse
out, Iceberg in, the domain unchanged — a real option rather than a claim, and
an import test asserts the domain never reaches past it.

## Approach

**The commit is one conditional write, and there is no current-snapshot
pointer.** The newest snapshot is the highest manifest version present. A
pointer would need its own atomicity and would be one more thing that can
disagree with the manifests it points at.

**Data files are written before the manifest that names them.** A lost race
leaves an orphan, which is garbage rather than corruption because a reader only
opens files a manifest lists. The other order produces a manifest naming files
that may never arrive.

**Identity is over rows, not bytes** ([[ADR-053]]). Parquet's footer carries its
writer's version, so a byte digest changes on a dependency upgrade — and a
dataset that renames itself when nobody touched it makes PRD §0 item 13
worthless.

**The research extract goes through the port**, not through an `s3://` glob. A
glob reads whatever is under a prefix at that moment, orphans included: a
different question with the same shape.

## Complexity Tracking

> No violations.
