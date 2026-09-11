---
id: OUT-2026-09-11-requirement-iceberg
step: requirement
records: [REQ-WP-039]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-039.md` and [[ADR-060]]. The canonical plane
migrates from a hand-rolled table layer to Apache Iceberg.

## What was decided

- **This is not a new architecture; it is the one [[ADR-002]] already chose.**
  That decision said "Parquet on S3-compatible object storage with Iceberg table
  semantics" and what got built implements those semantics rather than using
  them. [[REQ-WP-038]] found the first divergence that matters: the layer can
  only append, so nothing it offers can make a data file unreferenced, so
  retention has nothing to free.

## A diagnosis of mine that was wrong, corrected before it cost anything

[[ADR-060]] first said Iceberg avoids this because its manifests are per-commit
rather than cumulative, so expiring old snapshots unreferences their files.
**That is false**, and measuring it took ten minutes: four appends, expire two
snapshots, all four data files still referenced. Expiry alone frees nothing in
Iceberg either — the current snapshot sees every live file whatever the history
looks like.

The true difference is narrower: our table can only append. Iceberg has
`delete(row_filter)`, which rewrites the live file set and is measurably the
operation that makes a file unreferenced. The ADR carries the correction and the
measurement.

Second time in two requirements that a confident causal story survived four
artifacts and died on contact with a probe — the first was the backup's copy
ordering. Both times the story was plausible, load-bearing, and untested,
and both times ten minutes of measurement settled it. The lesson is not to
write fewer stories; it is to measure them before they reach a document.
- **Replace rather than keep both.** Two table implementations would be the
  second production path [[ADR-002]] refused when it rejected developing against
  a filesystem — one that diverges from production and is exercised by nobody
  until it matters.
- **The catalog is SQL: SQLite locally and in the fast gate, PostgreSQL on the
  stack.** Same implementation, different URL — which is the line [[ADR-002]]
  drew between a test double and a second path. REQ-INFRA-002's rule that a
  commit may not require a running service survives.
- **[[ADR-053]]'s content hash stays ours.** Iceberg allocates snapshot ids, so
  identical data gets different ids across runs, and PRD §0 item 13's
  reproducibility claim is built on a hash of the rows.
- **The acceptance is about not losing anything.** The migration's failure mode
  is not a crash — it is arriving with a working Iceberg table that quietly
  stopped doing one of the things the old one guaranteed. Every criterion names
  one of those things.

## What is still open

- **The migration is staged**, and the requirement stays open until the last
  caller moves and the old format is gone. A half-migrated plane is the state
  this requirement most needs to leave quickly.
- **[[REQ-WP-038]] stays `specified`**, blocked on this and unblocked by it. Its
  spec needs no change: Iceberg makes retention possible and decides nothing
  about what retention may not touch.
- **Whether `raw` payloads stay plain Parquet.** §6.4.4 explicitly allows it
  where "Iceberg metadata adds no value", and nothing writes a raw zone yet.
