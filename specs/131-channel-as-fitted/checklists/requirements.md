# Specification Quality Checklist: The chart draws the channel as the model fitted it

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] No implementation details beyond the formula the model defines
- [x] Requirements testable (SC-001 exact; SC-002 against live data)
- [x] Scope bounded (no corridor, no filled band, no per-bar history)
- [x] Edge cases identified (gaps, early snapshot, lookback one, zero slope, refit)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Principle I is engaged and held: the window ends at the snapshot's own instant, so nothing drawn uses bars
after it.
