# Plan: Compact the tail

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-105]]

Decision: `compact(big_rows=BIG_FILE_ROWS)` takes the live files in commit order, finds the last file with at least `big_rows` rows and replaces only
the ones after it (REQ-WP-100's replace-exact-files commit, its recorded order). Rejected: a size-tiered scheme with several levels (more machinery
than a table of this size needs); a time-based cutoff (the property wanted is "the part that has not been compacted", which row count states directly).
