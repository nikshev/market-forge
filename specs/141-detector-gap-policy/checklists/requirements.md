# Specification Quality Checklist: Extremum detector and channel gap policy

**Created**: 2026-10-06
**Feature**: [spec.md](../spec.md)

- [x] Facts read from the code (channel lookback, detector bar-counting, ETHUSDT 1h 148-bar hole measured)
- [x] Requirements testable (SC-001 detector restart, SC-002 channel post-gap fit, SC-003 threshold config, SC-004 lag time + no straddling)
- [x] Scope bounded (only channel + detector; not filling, not bridging, not all models)
- [x] Edge cases identified (threshold boundary, multiple holes, hole at boundaries, detector state at boundary)
- [x] No [NEEDS CLARIFICATION] markers — policy 2 assumed per recommendation; owner confirmation needed

## Notes

Key decision: policy 2 (restart at gap) assumed per requirement's recommendation. Owner confirmation needed before implementation — this spec stays `draft` until confirmed. The acceptance criteria are derived from PRD rules (§13.1, §15, §18, §32) assuming policy 2.