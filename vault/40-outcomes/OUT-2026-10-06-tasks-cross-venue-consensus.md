---
id: OUT-2026-10-06-tasks-cross-venue-consensus
step: tasks
records: [REQ-WP-091]
commit: null
---

## What was done

Ran `/speckit-tasks` on the planned requirement, producing `specs/140-cross-venue-consensus/tasks.md` with 33 tasks across 8 phases (Setup, Foundational, US1-US5, Polish). Then ran `/speckit-analyze` across spec.md, plan.md, and tasks.md.

## What was decided

- **Task structure follows 5 user stories** (US1-US5) each with independent tests first, then implementation. Enables incremental delivery.
- **Foundational phase (T002-T006)** is critical path: config, quotes/consensus tables, FeatureSpec registration, pane list.
- **US1 (library)** verifies existing `crossvenue.consensus_mid` covers all acceptance — no new code, just test coverage.
- **US2 (API)** adds two endpoints: `/consensus` and `venue_basis_bps` feature.
- **US3 (chart)** adds consensus line layer (optional, off by default).
- **US4 (pane)** adds `venue_basis_bps` to pane selector and line series rendering.
- **US5 (mixed types)** enforces consensus per market type via registry; test pins rule.
- **Trace markers**: T032 requires `@pytest.mark.trace("REQ-WP-091")` and `// @trace: REQ-WP-091` on touched files.

## What is still open

- **Analysis findings (5 MEDIUM, 1 LOW)** in `analysis-report.md`:
  - B1: Verify `consensus_mid` signature matches spec
  - C1: API needs `timeframe_ns` param (already in quickstart)
  - C2: Table schemas need `market_type` and explicit timestamps
  - C3: Registry market_type lookup confirmation
  - F2: FeatureSpec registration pattern
- These will be resolved during test-first implementation.

## Notes

All 13 requirements (7 FR + 6 SC) have ≥1 task. Coverage 100%. Constitution gates pass. The tasks.md is immediately executable.