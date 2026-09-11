# Implementation Plan: The canonical plane migrates to Apache Iceberg

**Branch**: `wp-039-iceberg` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

Step one of a staged migration: `lakehouse/iceberg.py`, an Iceberg-backed table
with the surface the hand-rolled one already has, plus the file accounting
retention needs. No caller moves yet.

## Technical Context

**Language**: Python 3.12 · **New dependency**: `pyiceberg[sql-sqlite]>=0.12`

**Testing**: the nine properties of [[REQ-WP-039]]'s acceptance, each with a
test; a mutation sweep; the existing suites untouched.

**Constraints**: the fast gate stays service-free — SQLite catalog, local
warehouse directory.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead** | Point-in-time reads compose knowledge and event time; see the measurement below. | **Pass.** |
| **VII. Live and replay are the same code** | One catalog implementation, two URLs. | **Pass.** |
| **XI. Reproducible results** | [[ADR-053]]'s row hash stays ours, because Iceberg allocates ids. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-039`, markers on every test. | **Pass.** |

No violations.

## The open question, measured

The spec left one open: does a point-in-time read use Iceberg's snapshot lookup
or a row filter over event time? Measured rather than guessed, with a table
whose second commit **backfills earlier rows** — which this system's replays do:

```text
commit 1: event times 100, 200
commit 2: event times  10,  20     (a backfill)

read by snapshot id 1     -> 100, 200
read by filter <= 200     -> 10, 20, 100, 200
```

They are different questions. The snapshot answers *what was known*; the filter
answers *what had happened*. PRD Principle I asks for both at once — "data with
`event_time <= t` **that was actually available then**" — and the hand-rolled
`read` already composes them: pick the snapshot, then filter within it.

That composition carries over exactly, as `scan(snapshot_id=..., row_filter=...)`.
The migration preserves the semantics rather than choosing between them, which
is the answer the measurement gave and not the one either option alone suggests.

## Project Structure

```text
pyproject.toml                               # + pyiceberg
src/channelflow/lakehouse/iceberg.py         # NEW
src/channelflow/lakehouse/__init__.py        # + exports
tests/unit/lakehouse/test_iceberg.py         # NEW
```

## Identity, and what changes

[[ADR-053]] says a dataset's identity is a hash of its rows, never of its bytes,
because a Parquet writer's version lives in the footer. Iceberg does not offer
this: its snapshot ids are allocated, so two runs over identical data get
different ones.

The hash is therefore computed here, over the rows a snapshot can see, in the
schema's own canonical encoding — the same rule as before, applied to a
different file layout. **The values will not match the old format's**, because
the old hash was a digest over per-file digests and this one is over the rows.
The property that matters is preserved and the numbers are not, which is stated
here rather than discovered by whoever compares two vaults.

## Snapshot ids stay small integers

Callers use `1, 2, 3`. Iceberg allocates 64-bit ids. The table maps between
them by commit order, so `snapshot_ids()`, `snapshot(n)` and `read(snapshot_id=n)`
keep their meaning and FR-010 holds. The Iceberg id is available for anything
that needs to talk to Iceberg directly, and nothing in the domain does.

## What retention needs, delivered here

`unreferenced_files()`: every object under the table's location that no live
snapshot's scan plans. After a delete and an expiry that is exactly the set
retention removes, and producing it here rather than in `retention.py` keeps the
knowledge of Iceberg's layout in one module.
