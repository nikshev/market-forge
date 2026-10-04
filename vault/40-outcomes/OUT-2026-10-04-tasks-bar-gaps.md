---
id: OUT-2026-10-04-tasks-bar-gaps
step: tasks
records: [REQ-WP-086]
commit: null
---

## What was done

14 tasks, tests first. `speckit-analyze` found one medium and three low issues; all fixed in the artifacts.

## What the analysis found, and how it was resolved

- **F1 (MEDIUM): how the pane decides a CVD run starts at a gap.** The spec said it; the plan and tasks did not say how. A run
  also starts after a trade-id break, where nothing is missing from the bars, so the run number cannot be the test. The pane
  intersects the gap markers' times with the run's first point (plan D6, T005).
- **F2 (LOW):** a stale series (an old last bar) is not a hole; noted as freshness, [[REQ-WP-090]]'s.
- **F3 (LOW):** the live hole may be closed by a backfill, so the tests use fixtures and the screenshot records its date.
- **F4 (LOW):** a self-contradicting task title was made plain.

## What is still open

- Nothing blocking implementation.
