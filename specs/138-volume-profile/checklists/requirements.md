# Specification Quality Checklist: A volume profile beside the price axis

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] Facts read from the code (the profile builder reads trades; no trade is stored; bars have no price inside; the primitives API; the ingest seams)
- [x] The cost of the design is stated (no history; thin first hours; coverage is part of the answer)
- [x] Requirements testable (SC-001..SC-004)
- [x] Scope bounded (no backfill, no HVN/LVN, no lower pane, no notional)
- [x] Edge cases identified (width drift, unknown-only bins, one bin, ties, resize)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Collection starts at deployment, so the first screenshots are of a thin profile and say so.
