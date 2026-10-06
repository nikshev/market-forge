## Specification Analysis Report: REQ-WP-087 (141-detector-gap-policy)

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Underspecification | MEDIUM | spec.md:FR-006, tasks.md:T002 | `gap_threshold` default 1 means 1 missing bar = bridge, 2+ = hole. Need to confirm this matches "hole of more than one timeframe step" from requirement | Verify in T007/T012 tests: threshold=1 → 1 missing = contiguous |
| C2 | Underspecification | MEDIUM | spec.md:US2, tasks.md:T011 | Channel `window.py` `select_window()` signature and return type — need to verify exact function to modify | Inspect `src/channelflow/channels/window.py` before implementation |
| F1 | Inconsistency | LOW | spec.md:US1 "confirmation_lag_bars" vs FR-007 "confirmation_lag_ns" | Spec mentions both; FR-007 adds `confirmation_lag_ns` alongside existing `confirmation_lag_bars` | No change needed; both fields exist |

### Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | ✅ | T006, T007, T010 | Gap detection helper |
| FR-002 | ✅ | T007, T008 | Detector reset |
| FR-003 | ✅ | T007, T008 | No straddling confirmation |
| FR-004 | ✅ | T010, T011 | Channel post-gap fit |
| FR-005 | ✅ | T010, T011 | Snapshot absent/short |
| FR-006 | ✅ | T002, T003, T012, T013 | gap_threshold config |
| FR-007 | ✅ | T009, T014 | confirmation_lag_ns |
| FR-008 | ✅ | T007, T008, T015, T017 | No straddling records |
| SC-001 | ✅ | T007 | Detector restart |
| SC-002 | ✅ | T010 | Channel post-gap |
| SC-003 | ✅ | T012 | Threshold config |
| SC-004 | ✅ | T014, T015, T017 | Lag_ns + no straddling live |
| SC-005 | ✅ | T019, T020 | Existing tests |

### Constitution Alignment Issues

None — all principles pass.

### Unmapped Tasks

- T001: Baseline (setup)
- T019-T021: Polish/commit (cross-cutting)

### Metrics

- Total Requirements (FR + SC): 13
- Total Tasks: 21
- Coverage %: 100%
- Ambiguity Count: 0
- Critical Issues: 0

## Next Actions

Proceed to `/speckit-implement` — tasks are complete, testable, and constitution-aligned. The MEDIUM items (C1, C2) will be resolved during test-first implementation.