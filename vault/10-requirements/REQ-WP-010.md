---
id: REQ-WP-010
title: Backtest v1
type: work-package
prd_ref: "WP-010 Backtest v1"
prd_lines: "7004-7010"
phase: null
status: specified
depends_on: ["REQ-WP-005", "REQ-WP-007"]
tags: []
---

## Requirement

- virtual clock;
- bar replay;
- strategy reuse;
- reports.

## Acceptance

- backtest runs on a virtual clock;
- backtest replays bars;
- backtest reuses the live strategy/signal engine rather than a separate implementation;
- backtest produces reports.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-009-backtest-v1]]
- **Outcomes:** [[OUT-2026-09-08-spec-backtest-v1]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
