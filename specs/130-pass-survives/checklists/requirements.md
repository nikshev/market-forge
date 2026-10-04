# Specification Quality Checklist: A background pass that fails is reported and tried again

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] No implementation details beyond the one design fact (the next pass is the retry; the interval is fixed)
- [x] Requirements testable and unambiguous (FR-002 pins one traceback per run)
- [x] Success criteria measurable (SC-002 counts tracebacks; SC-003 four intervals)
- [x] Scope bounded: no backoff, no in-pass retry, no change to `maintenance` or ingest
- [x] Edge cases identified (first pass, start-up, never-clearing failure)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Principles in play: XII (a process that dies on a transient fault is a correctness-adjacent weakness), and the
repository's own rule that a repeated condition does not repeat its full report.
