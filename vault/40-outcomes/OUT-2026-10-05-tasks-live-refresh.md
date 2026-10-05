---
id: OUT-2026-10-05-tasks-live-refresh
step: tasks
records: [REQ-WP-090]
commit: null
---

## What was done

Ran `/speckit-tasks` on the planned requirement, producing `specs/139-live-refresh/tasks.md` with 28 tasks across
7 phases (Setup, Foundational, US1, US2, US3, US4, Polish). Then ran `/speckit-analyze` across spec.md, plan.md,
and tasks.md.

## What was decided

- **Task structure follows user stories exactly**: 4 user stories (US1-US4) each with independent tests first, then
  implementation. This enables incremental delivery and isolated validation.
- **Foundational phase (T002-T006) is the critical path**: timer config, `isLoading`/`isInitialLoad` refs, visibility
  listener, and `Chart` range preservation must all land before any story can run.
- **T005/T006 `isInitialLoad` prop** is the key design decision for range preservation — explicit prop from `App.tsx`
  (knows trigger: mount/deps = initial, timer = refresh) rather than comparing data identity. Simpler and matches
  spec's "only initial load (or timeframe/mode change) may set the range".
- **Tests written first**: T007-T009 (US1), T014 (US2), T017-T020 (US3) are test tasks that will RED before
  implementation. Existing test patterns in `chartTimeframeControl.test.tsx` and `appProfile.test.tsx` are the model.
- **Trace markers**: T009, T025 require `@pytest.mark.trace("REQ-WP-090")` and `// @trace: REQ-WP-090` on all
  touched files.

## What is still open

- **Analysis findings (5 MEDIUM, 1 CRITICAL-verified, 3 LOW)** documented in `analysis-report.md`:
  - B1: Range preservation mechanism (library retains pan/zoom by not resetting) — will be verified by T008
  - C1: Timeframe/mode change supersedes via `loadId` while refresh in flight — existing behavior, acceptable
  - C2: `isInitialLoad` signaling mechanism — implemented in T005/T010
  - E2: Byte-identical history after refresh — add assertion in T019
  - F1: `fetchVolumeProfile` included in refresh — already in `load()` when `wantsProfile`
- These will be resolved during test-first implementation (the RED tests force exact behavior).

## Notes

All 14 requirements (9 FR + 5 SC) have ≥1 task. Coverage 100%. Constitution gates pass (Principle I verified,
Principle X via build-time Vite env). The tasks.md is immediately executable — each task has file paths and clear
acceptance from the test tasks.