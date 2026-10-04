---
id: OUT-2026-10-04-tasks-volume-profile
step: tasks
records: [REQ-WP-089]
commit: null
---

## What was done

25 tasks, tests first, in four phases. `speckit-analyze` found three medium and three low issues; all fixed in the artifacts.

## What the analysis found, and how it was resolved

- **F1 (MEDIUM): the width was "configurable" with no variable, grammar or plumbing.** Named `CHANNELFLOW_PROFILE_BIN_WIDTHS` and `CHANNELFLOW_PROFILE_BLOCK_SECONDS`;
  T008 now covers the settings, `docker-compose.yml`, `.env.example` and `docs/deployment.md`, and T002 the grammar's refusals.
- **F2 (MEDIUM): "beside the axis" had no placement.** Anchored at the plot's right edge, growing leftwards, the busiest bin at most a quarter of its width.
- **F3 (MEDIUM): SC-002 compared indices that cannot match.** `build` renumbers bins by position and anchors at the minimum price; ours are real indices from zero.
  The comparison is by bin edges and volumes, with `build(anchor=0)`.
- **F4-F6 (LOW):** the deep link's instant; the up-to-five-minute lag of whole blocks; the requirement's stale dependency on REQ-WP-088.

## What is still open

- Nothing blocking implementation.
