# Specification Quality Checklist: The chart follows the market without a reload

**Created**: 2026-10-05
**Feature**: [spec.md](../spec.md)

- [x] Facts read from the code (single load, range reset on every data change, loadId guard, LoadState vocabulary, reader state, pinned branch, 5-minute producer floor)
- [x] Requirements testable (SC-001 new bar in one interval, SC-002 five pieces of state unchanged, SC-003 zero/one requests, SC-004 failure then recovery)
- [x] Scope bounded (stage 1 only; push explicitly out as FR-009)
- [x] Edge cases identified (refused set, failed/empty first load, forming bar, out-of-order answers, unmount, bad interval, Principle III)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Stage 2 (push through `/ws/market`) is the requirement's own split point and is recorded as out of scope here rather than
left ambiguous. The interval default (60 s) is the requirement's, not a guess.
