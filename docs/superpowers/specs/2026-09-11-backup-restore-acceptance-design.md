# Deriving acceptance for backup/restore (REQ-WP-037)

**Date**: 2026-09-11 · **PRD**: `channel_flow_prd_codex_ua_v5.md` (read-only)

PRD §45's Phase 8 lists `backup/restore;` and gives it no section of its own.
Every criterion below is therefore **derived, not quoted**, and each names the
PRD text it is derived from. This document exists so the derivation can be
disagreed with.

---

## 1. A backup is a claim about restoring, so the test restores

**From**: §0 item 13 (a result reproducible from "a versioned dataset + config +
code commit hash + model artifact hash") and §6.4.3 ("retention must be long
enough for operational replay/recovery").

Both sentences describe recovery as an operation somebody performs, not as bytes
that exist. A backup nobody has restored is an untested code path holding the
data of last resort, and the moment it is exercised is the moment it must not
fail. The criterion is therefore about the round trip, not about the copy.

## 2. Verified by content hash, not by byte equality

**From**: §29.B ("Every research-grade table must support dataset
lineage/snapshot reproducibility") via [[ADR-053]].

ADR-053 already established that Parquet bytes carry the writer's version in the
footer, so an identical dataset written after a library upgrade has different
bytes. `Snapshot` consequently carries two digests: `content_sha256` over the
rows and `file_sha256` over the stored bytes.

A restore verified on bytes fails spuriously after an upgrade and teaches
whoever is restoring at 3am to ignore the check. A restore verified on nothing
proves the files exist. The content hash is the only one that answers "is this
the dataset that was backed up".

Byte equality is still worth asserting where it is genuinely expected — a copy
that did not re-encode anything — so both are checked, and the criterion says
which failure means what.

## 3. Data files before the manifests that name them

**From**: §6.4.4's S3 zones and `lakehouse/table.py`'s own invariant, which is
itself derived from §0.5's append-only rule.

The writer's ordering is not an implementation detail: "a commit that dies
halfway leaves orphan data files, which is not corruption — a reader only ever
opens files a manifest lists. The alternative produces a manifest naming files
that may not arrive, which *is* corruption."

A backup that copies in any other order manufactures exactly that corruption in
the copy, and a restore from it produces a table that reads fine until it
touches the missing file. The backup inherits the writer's ordering because it
inherits the writer's invariant.

## 4. A silent landing on an earlier snapshot is data loss

**From**: §0.5 (a finalized record is never rewritten) and §29.B's lineage
requirement.

The canonical plane is append-only and versioned, so restoring to an earlier
point in time is a legitimate operation — and one that is indistinguishable,
afterwards, from having lost the newer commits. The criterion is not "always
restore the latest"; it is that the restore **states which snapshot it landed
on**, and that landing short of the newest snapshot in the backup is something
the operator asked for rather than something that happened.

## 5. Restoring into a non-empty target is refused

**From**: §0.5, and §6.4.3's "all consumers must be replay-safe and idempotent
where materialization occurs".

Merging a backup into a table that already holds data produces a version history
that never existed: manifests from two lineages under one sequence. Idempotent
means restoring twice is safe, not that two different histories can be blended.
Refusal is the only outcome that cannot silently corrupt lineage.

## 6. Verified against the real object store

**From**: CLAUDE.md's two-gate rule and [[ADR-002]] (S3-compatible storage is
the canonical plane precisely so local and production do not diverge).

`REQ-STORE-001` already argued this for the table layer: a double that raises
the error it was told to raise proves the mapping, not the guarantee. A backup
is the one thing that must work against the real backend, so the round trip runs
as an integration test on MinIO in CI, with the in-memory store carrying the
logic tests.

---

## What is deliberately not derived

- **A retention or schedule policy.** §6.4.9 covers retention tiers and §45
  lists "S3 cold retention" as its own deliverable. How long backups are kept is
  that deliverable's, not this one's.
- **Postgres metadata.** The canonical plane is object storage ([[ADR-002]]) and
  the Postgres schema holds operational metadata that is rebuilt rather than
  restored. Naming it here would claim a guarantee nothing implements.
- **Encryption or off-site replication.** §34's security section covers
  credentials and separation of concerns and says nothing about backup
  encryption; inventing a criterion would be writing requirements, not deriving
  them.
