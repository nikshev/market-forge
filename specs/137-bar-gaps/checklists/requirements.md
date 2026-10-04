# Specification Quality Checklist: A missing bar is visibly missing

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] Facts read from the code and the live API (the holes, the single `setMarkers` call, the bar windows, the index axis)
- [x] Requirements testable (SC-001 counts, SC-002 ordering, SC-003 the real hole)
- [x] Scope bounded (no time-true axis, no backfill, no model behaviour)
- [x] Edge cases identified (ends, unsorted, corrected bar, zero volume, many holes)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

A marker cannot carry a span; the notice does. The requirement's acceptance was amended to say so.
