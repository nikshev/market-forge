---
id: OUT-2026-09-11-requirement-backup-restore
step: requirement
records: [REQ-WP-037]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-037.md`, plus the derivation document
`docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.
One of [[REQ-PHASE-8]]'s six open deliverables.

PRD §45 names the deliverable and gives it no section, so every acceptance line
is derived and each names the PRD text behind it — the same treatment
[[REQ-WP-016]] and the phase notes received.

## What was decided

- **The acceptance is about the round trip, not the copy.** §0 item 13 and
  §6.4.3 both describe recovery as an operation someone performs. A backup
  nobody has restored is an untested code path holding the data of last resort.
- **Verified on `content_sha256`, not on bytes.** [[ADR-053]] already
  established that Parquet footers carry the writer's version, so identical data
  written after a library upgrade has different bytes. A byte-verified restore
  fails spuriously after an upgrade and teaches whoever is restoring at 3am to
  ignore the check. Both digests are still asserted, because they answer
  different questions and their failures mean different things.
- **The copy inherits the writer's ordering**, and this is the line the
  requirement would have missed without reading `table.py`'s own docstring. Data
  files before manifests: orphan files are invisible to readers, a manifest
  naming absent files is corruption. Any other copy order manufactures that
  corruption in the backup.
- **A silent landing on an earlier snapshot is data loss wearing the shape of
  success.** Restoring to an earlier point is legitimate; doing it by accident
  is indistinguishable from it afterwards. So the restore states where it landed
  and refuses to land short unless asked.
- **Three things are named as out of scope in the derivation** rather than
  quietly omitted: retention (a separate Phase 8 line), Postgres metadata
  (rebuilt, not restored), and encryption (§34 says nothing, and a criterion
  there would be writing requirements rather than deriving them).

## What is still open

- **Whether the backup should be incremental.** The canonical plane is
  append-only, so copying only new objects is natural and is also where a subtle
  bug would live. Not decided here.
- **Where a backup lives.** A second bucket, a second endpoint, or a local
  directory are all defensible and the choice is a deployment one.
