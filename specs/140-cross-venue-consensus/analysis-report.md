## Specification Analysis Report: REQ-WP-091 (140-cross-venue-consensus)

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| B1 | Ambiguity | MEDIUM | spec.md:FR-001, tasks.md:T008 | `consensus_mid` already exists in library; T008 says "verify it already enforces all rules" — need to confirm exact function signature matches spec (quotes format, staleness param) | Add verification step in T008: inspect `crossvenue/consensus.py` function signature and docstring |
| C1 | Underspecification | MEDIUM | spec.md:FR-002, plan.md | API `/consensus` needs `timeframe_ns` to know bar boundaries; spec mentions window but not timeframe param | Add `timeframe_ns` to API contract (already in quickstart example) |
| C2 | Underspecification | MEDIUM | tasks.md:T003, T004 | Table schemas need to include `market_type` in consensus table; `quotes` table needs `exchange_time` vs `ingest_time` distinction | Update data-model.md and table schemas to include `market_type` and explicit timestamp fields |
| C3 | Underspecification | MEDIUM | spec.md:FR-006, tasks.md:T026 | How does registry provide market_type? `instrument_metadata` [[REQ-WP-060]] has it, but need to confirm API | Add note in T026: use existing `instrument_metadata` lookup |
| F1 | Inconsistency | LOW | spec.md:US2 "same windows as volume profile" vs FR-002 "4h, 24h, 7d" | Volume profile uses 4h/24h/7d — consistent, but should reference explicitly | No change needed; already consistent |
| F2 | Inconsistency | LOW | tasks.md:T005 FeatureSpec registration vs FR-005 "registered with FeatureSpec" | T005 says add to `features/__init__.py` but FeatureSpec may be registered elsewhere | Verify FeatureSpec registration pattern in codebase |

### Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | ✅ | T007, T008 | consensus_mid library |
| FR-002 | ✅ | T010, T012, T013, T014 | API consensus |
| FR-003 | ✅ | T011, T012, T013, T014 | API venue_basis_bps |
| FR-004 | ✅ | T015, T016, T017, T018, T019 | Chart consensus line |
| FR-005 | ✅ | T020, T021, T022, T023, T024 | Basis pane |
| FR-006 | ✅ | T025, T026, T027, T028 | Mixed types |
| FR-007 | ✅ | T031, T032 | Screenshots |
| SC-001 | ✅ | T007 | Median/exclusions |
| SC-002 | ✅ | T007 | No look-ahead |
| SC-003 | ✅ | T010, T011 | API responses |
| SC-004 | ✅ | T015 | Chart line/gaps |
| SC-005 | ✅ | T020 | Pane/feature |
| SC-006 | ✅ | T030 | Existing tests |

### Constitution Alignment Issues

None — all principles pass.

### Unmapped Tasks

- T001: Baseline (setup)
- T029-T033: Polish/commit (cross-cutting)

### Metrics

- Total Requirements (FR + SC): 13
- Total Tasks: 33
- Coverage %: 100%
- Ambiguity Count: 1
- Critical Issues: 0

## Next Actions

1. **MEDIUM (B1, C1, C2, C3, F2)** — minor clarifications resolved during implementation (TDD tests will force exact behavior)
2. Proceed to `/speckit-implement` — tasks are complete, testable, and constitution-aligned

## Remediation Offer

Would you like me to suggest concrete edits for the top 4 issues before implementation?