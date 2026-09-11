---
id: OUT-2026-09-11-spec-retention
step: spec
records: [REQ-WP-038]
commit: null
---

## What was done

`specs/076-retention/spec.md`: four user stories, 11 functional requirements,
7 success criteria. [[REQ-WP-038]] moves to `specified`.

## What was decided

- **FR-005 makes the feature almost do nothing, and that is correct.**
  Manifests are cumulative, so a file from the first commit is named by every
  later manifest and cannot be removed until all of them are expired. A spec
  that skipped this produces a pass which deletes files a surviving snapshot
  still needs — and that reads as "retention works" right up to the first
  point-in-time query.
- **Removal is the inverse of writing.** Manifest first, then what it uniquely
  named. Pruning in the writing order opens a window where the table is broken,
  and an interrupted pass makes the window permanent.
- **The newest snapshot survives any policy.** A table with no current state is
  not retained; it is deleted with extra steps.
- **A pin naming an absent snapshot is refused**, which is a judgement call. It
  could be ignored, but the likeliest cause is a typo, and ignoring it prunes
  something somebody meant to keep — the one outcome here that cannot be undone.
- **Verification is [[REQ-WP-037]]'s**, unchanged. "No manifest names an absent
  file" is the same property whichever operation might have broken it, and a
  second checker would drift from the first.

## What is still open

- **Whether an unpinned prune needs an explicit acknowledgement.** It is
  legitimate, and it is also exactly what someone does by accident when the
  lineage source is missing — which, per the requirement's finding, it currently
  is.
- **Nothing schedules a pass.**
