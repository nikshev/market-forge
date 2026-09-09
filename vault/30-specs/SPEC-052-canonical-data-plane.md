---
id: SPEC-052-canonical-data-plane
requirement: REQ-STORE-001
speckit_path: specs/052-canonical-data-plane/spec.md
status: draft
---

## Summary

PRD §7's target storage profile, which [[ADR-002]] chose on the project's first
day and nothing had built since: Parquet on S3-compatible object storage as the
canonical durable data plane, with Iceberg table semantics over it and DuckDB
for bounded research extracts.

"Iceberg semantics" here means the four properties §29.B needs rather than the
file format that carries them elsewhere — immutable snapshots, atomic commits,
versioned schemas, and a dataset identity a research run can be pinned to.

The commit is one conditional write. There is no current-snapshot pointer: the
newest snapshot is the highest manifest version present, so a race is resolved
by whoever wins that write and a loser leaves an orphaned data file that no
reader can see, because a reader only ever opens files a manifest names.

The identity is a hash of the rows, never of the files ([[ADR-053]]). Parquet
writes its own version into every footer, so a byte digest changes when a
dependency is upgraded — and a dataset that renames itself while nobody touches
it makes PRD §0 item 13's reproducibility claim worthless.

## Links

- Requirement: [[REQ-STORE-001]]
- Decision: [[ADR-053]]
- Builds on: [[REQ-WP-001]], [[REQ-WP-002]]
- Unblocks: [[REQ-PHASE-6]]'s dataset hashes, [[REQ-API-001]]'s durable repository ([[ADR-019]])
