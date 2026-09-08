---
id: REQ-WP-009
title: Chart
type: work-package
prd_ref: "WP-009 Chart"
prd_lines: "6995-7003"
phase: null
status: implemented
depends_on: ["REQ-API-001", "REQ-WP-005", "REQ-WP-006", "REQ-WP-007"]
tags: []
---

## Requirement

- candles;
- channel;
- zones;
- marker;
- historical snapshot mode;
- realtime WS.

## Acceptance

- chart renders candles;
- chart renders the channel overlay;
- chart renders zones;
- chart renders markers;
- chart supports a historical snapshot mode;
- chart updates over a realtime WebSocket.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-013-chart-and-read-api]]
- **Tests:**
    - `tests/unit/api/test_channel_modes.py::test_the_parameter_defaults_to_as_seen_then`
    - `tests/unit/api/test_channel_modes.py::test_the_two_modes_disagree_and_that_is_the_point`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/ChannelMode.tsx`
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/LoadState.tsx`
    - `apps/web/src/__tests__/ChannelMode.test.tsx`
    - `apps/web/src/__tests__/Chart.test.tsx`
    - `apps/web/src/__tests__/LoadState.test.tsx`
    - `apps/web/src/__tests__/scaffold.test.tsx`
    - `apps/web/src/api.ts`
    - `apps/web/src/deepLink.ts`
    - `apps/web/src/series.ts`
    - `apps/web/src/test-setup.ts`
    - `apps/web/src/types.ts`
    - `apps/web/src/vite-env.d.ts`
    - `apps/web/vite.config.ts`
- **Outcomes:** [[OUT-2026-09-08-implement-chart-and-read-api]], [[OUT-2026-09-08-plan-chart-and-read-api]], [[OUT-2026-09-08-spec-chart-and-read-api]], [[OUT-2026-09-08-tasks-chart-and-read-api]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
