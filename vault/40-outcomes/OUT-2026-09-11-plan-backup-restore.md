---
id: OUT-2026-09-11-plan-backup-restore
step: plan
records: [REQ-WP-037]
commit: null
---

## What was done

`specs/075-backup-restore/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/backup.md`, `quickstart.md`. [[REQ-WP-037]] moves to `planned`.

## What was decided

- **The copy walks snapshots; it does not list keys.** Listing is shorter and
  wrong: a sorted listing returns `<table>/metadata/v00000001.json` before
  `<table>/data/...`, so the obvious implementation copies manifests first —
  exactly the ordering `table.py` calls corruption. The bug is invisible in any
  test that lets the copy finish, which is why the tests interrupt it.
- **Walking gives the interruption property for free**: stop anywhere and the
  copy is a prefix of the history, every manifest fully backed by its data.
- **`get` + `put_if_absent`, not a new port operation.** A server-side copy
  exists on S3 and would have to be emulated by the in-memory store for an
  operation the table layer does not need; the port is deliberately "what the
  table layer needs, and nothing more". `put_if_absent` also makes re-running an
  interrupted backup safe by construction — already-copied objects are skipped,
  and an object whose content differs raises instead of being overwritten.
- **`verify` returns a report, not a boolean.** Missing file, byte mismatch and
  identity mismatch are three different answers to the 3am question, and only
  one of them means "retry".
- **Byte digests are checked despite [[ADR-053]].** That warning is about
  comparing re-encoded data; a copy re-encodes nothing, so byte equality is
  genuinely expected here. Identity still uses the content hash.
- **A module, not methods on `Table`.** A table that can copy itself elsewhere
  invites use as a general copy mechanism, which is how two lineages end up
  merged under one sequence.

## What is still open

- Nothing new. Incremental backup and where a backup lives both stand from
  [[OUT-2026-09-11-spec-backup-restore]].
