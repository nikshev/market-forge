# Phase 0 — Research

## 1. Does expiry free data? (No.)

**Measured**: four appends, expire two snapshots, count files.

    parquet before: 4    snapshots: 4
    parquet after : 4    snapshots: 2

**Finding**: expiry alone frees nothing, because the current snapshot still
references every live file. This corrected [[ADR-060]], which had claimed the
opposite from reasoning about manifest layouts.

## 2. What does free data, then?

**Measured**: `delete(row_filter)`.

    one file, 4 rows -> delete("event_time_ns < 3")
    -> 2 files on disk, 1 referenced, 2 rows visible

**Finding**: a delete rewrites the live file set, dropping files whose rows all
match and copy-on-write rewriting one that straddles the cutoff. That is the
operation our table does not have and cannot be given without becoming Iceberg.
Retention is then three steps: delete, expire, remove what nothing references.

## 3. Snapshot or filter for a point-in-time read?

**Measured** with a backfilling second commit — the shape this system's replays
produce:

    commit 1: 100, 200 | commit 2: 10, 20
    by snapshot 1 -> 100, 200
    by filter<=200 -> 10, 20, 100, 200

**Finding**: neither, alone. The snapshot is the knowledge dimension and the
filter is the market-time dimension, and PRD Principle I names both. The
hand-rolled `read` already composes them and the composition carries over
unchanged.

## 4. Which catalog?

**Decision**: `pyiceberg`'s SQL catalog — SQLite locally and in the fast gate,
PostgreSQL on the stack.

**Rationale**: REQ-INFRA-002 says a commit may not need a running service, and a
file-backed catalog satisfies that with the *same implementation* the stack
uses, differing only in a URL. That is the line [[ADR-002]] drew when it chose
MinIO over a local directory: a test double behind a port is fine, a second
production path is not.

## 5. What about the content hash?

**Decision**: computed here, over rows, as [[ADR-053]] requires.

**Rationale**: Iceberg allocates snapshot ids rather than deriving them, so two
runs over identical data get different ones and PRD §0 item 13's reproducibility
claim cannot rest on them. The values differ from the old format's, which is a
consequence worth stating: the old hash digested per-file digests, this one
digests rows. The rule is the same and the numbers are not.
