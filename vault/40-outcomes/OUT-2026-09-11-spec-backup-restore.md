---
id: OUT-2026-09-11-spec-backup-restore
step: spec
records: [REQ-WP-037]
commit: null
---

## What was done

`specs/075-backup-restore/spec.md`: four user stories, 11 functional
requirements, 7 success criteria. [[REQ-WP-037]] moves to `specified`.

## What was decided

- **SC-003 states a criterion about a state that cannot arise**, on purpose. A
  copy truncated *after* a manifest and before its data would fail verification
  — and FR-001's ordering is precisely what prevents it. There is no other way
  to make an ordering rule visible in success criteria: a criterion asserting
  only that backups succeed passes for an implementation copying manifests
  first, which is the one thing this feature must not do.
- **Verification is digest-based; the tests are row-based.** An operator
  restoring at 3am should not have to decode every Parquet file, so verification
  compares digests. But a digest check can only prove the manifests agree with
  the files — the rows are what somebody actually wanted back, so the suite
  reads both tables and compares them. Which check runs where is stated rather
  than left to taste, and it is the assumption a reviewer should push on.
- **Two failure kinds are reported apart.** A byte-digest mismatch says the copy
  was damaged in transit; a snapshot-identity mismatch says a different dataset
  arrived. Collapsing them into "verification failed" would make the 3am
  question — is this a retry or a disaster — unanswerable.
- **An orphan file is not a verification failure.** The writer already lives by
  that rule; a backup inventing a stricter one would report corruption where the
  system deliberately tolerates waste.
- **The backup is a store-to-store copy over the existing port**, so the target
  can be a second bucket, a second endpoint or a directory without this feature
  making a deployment decision.

## What is still open

- **Incremental backup.** The plane is append-only, so copying only new objects
  is natural and is exactly where a subtle bug would live.
- **Where a backup lives and on what schedule** — deployment questions, and
  retention is Phase 8's own separate deliverable.
