---
id: OUT-2026-10-06-tasks-detector-gap-policy
step: tasks
records: [REQ-WP-087]
commit: null
---

## What was done

Ran `/speckit-tasks` on the planned requirement, producing `specs/141-detector-gap-policy/tasks.md` with 21 tasks across 8 phases (Setup, Foundational, US1-US5, Polish). Then ran `/speckit-analyze` across spec.md, plan.md, and tasks.md.

## What was decided

- **Task structure follows 5 user stories** (US1-US5): US1 detector reset, US2 channel post-gap fit, US3 threshold config, US4 confirmation lag, US5 live validation.
- **Foundational phase (T002-T006)** is critical: config, extended records (confirmation_lag_ns, window_bars/window_short), shared gap detection helper `is_gap()`.
- **US1 (detector)** modifies `detector.py` `run()` loop: gap detection via `is_gap()`, state reset, no straddling confirmation.
- **US2 (channel)** modifies `window.py` `select_window()`: window starts after gap, `window_short` flag, `first_bar_after_gap_ns`.
- **US3 (config)** covered by T002/T003/T006 — `GAP_THRESHOLD` env var with default 1.
- **US4 (lag)** adds `confirmation_lag_ns` to extremum record; live validation on ETHUSDT 1h.
- **Trace markers**: `@pytest.mark.trace("REQ-WP-087")` and `# @trace: REQ-WP-087` on all touched files.

## What is still open

- **Analysis findings (2 MEDIUM, 1 LOW)** in `analysis-report.md`:
  - C1: Verify threshold=1 means 1 missing = bridge, 2+ = hole
  - C2: Inspect `window.py` `select_window()` signature before implementation
  - F1: Both `confirmation_lag_bars` and `confirmation_lag_ns` fields coexist
- These will be resolved during test-first implementation.

## Notes

All 13 requirements (8 FR + 5 SC) have ≥1 task. Coverage 100%. Constitution gates pass. The tasks.md is immediately executable.