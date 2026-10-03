---
id: SPEC-124-snapshot-single-load
requirement: REQ-WP-079
speckit_path: specs/124-snapshot-single-load/spec.md
status: draft
---

## Summary

A read of the newest snapshot of an Iceberg table loads the table, then loads it again to learn
which snapshot is newest, and looks that number up in the first load. With five writers on one
table a commit between the two raises `NoSuchSnapshot`: 14 times in about 13 hours across the
worker and the resample job, once fatally. The spec asks that each reading operation resolve
against one version of the table, keeps the honest error for a number that does not exist, keeps
pinned reads reproducible, and refuses the shortcut of making callers tolerate the error.

## Links

- Requirement: [[REQ-WP-079]]
- Found by: the logs after [[REQ-WP-078]]
