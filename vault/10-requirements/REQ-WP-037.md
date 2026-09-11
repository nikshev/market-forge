---
id: REQ-WP-037
title: A backup is a claim about restoring, so the test restores
type: work-package
prd_ref: "§45 Phase 8"
prd_lines: "6912"
phase: 8
status: planned
depends_on: [REQ-STORE-001]
tags: []
---

## Requirement

PRD §45's Phase 8 lists:

    - backup/restore;

and gives it no section of its own. The acceptance below is therefore
**derived, not quoted**; each line names the PRD text behind it in
`docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.

Two sentences elsewhere in the PRD say what a backup is for. §0 item 13 asks a
result to be reproducible from "a versioned dataset + config + code commit hash
+ model artifact hash", and §6.4.3 requires retention "long enough for
operational replay/recovery". Both describe recovery as something a person
performs, not as bytes that exist somewhere.

**A backup nobody has restored is an untested code path holding the data of last
resort**, and the moment it is exercised is the moment it must not fail.

Two more things follow from the canonical plane's own shape rather than from a
general idea of backups.

**The copy inherits the writer's ordering.** `lakehouse/table.py` writes data
files before the manifest naming them, and says why: a commit that dies halfway
leaves orphan files, which no reader can see, whereas a manifest naming files
that never arrived is corruption. A backup copying in any other order
manufactures that corruption in the copy, and the restored table reads correctly
until something touches the missing file.

**Landing on an earlier snapshot is a legitimate operation and a catastrophic
accident**, and afterwards the two are indistinguishable. The requirement is not
that a restore always lands on the newest snapshot; it is that it says which one
it landed on, and that landing short of the newest was asked for.

## Acceptance

- A backup can be restored, and the test performs the round trip rather than
  asserting that a copy exists.
- A restore is verified by `content_sha256` — the logical dataset — not by byte
  equality, which [[ADR-053]] already showed changes when a writer library is
  upgraded and nothing about the data has.
- Byte equality is asserted where it is genuinely expected, and a mismatch there
  means something different from a content mismatch; the two failures are
  reported apart.
- Data files are copied before the manifests that name them, and a backup
  interrupted partway leaves a restorable earlier state rather than a manifest
  naming absent files.
- A restore states which snapshot it landed on.
- Landing short of the newest snapshot in the backup is refused unless the
  caller asked for that snapshot by name.
- Restoring into a non-empty target is refused rather than merged.
- The round trip is verified against a real object store in CI, with the
  in-memory store carrying the logic tests ([[ADR-002]], CLAUDE.md's two gates).

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Deliberately out of scope, and argued in the derivation document: retention and
scheduling (§6.4.9 and Phase 8's own "S3 cold retention" line), Postgres
metadata (rebuilt, not restored), and encryption (§34 says nothing about it, and
inventing a criterion would be writing requirements rather than deriving them).
