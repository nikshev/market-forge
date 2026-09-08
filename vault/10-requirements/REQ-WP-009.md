---
id: REQ-WP-009
title: Chart
type: work-package
prd_ref: "WP-009 Chart"
prd_lines: "6995-7003"
phase: null
status: planned
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
- **Outcomes:** [[OUT-2026-09-08-plan-chart-and-read-api]], [[OUT-2026-09-08-spec-chart-and-read-api]], [[OUT-2026-09-08-tasks-chart-and-read-api]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
