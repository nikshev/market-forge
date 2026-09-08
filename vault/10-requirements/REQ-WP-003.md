---
id: REQ-WP-003
title: Binance connector
type: work-package
prd_ref: "WP-003 Binance connector"
prd_lines: "6945-6958"
phase: null
status: specified
depends_on: [REQ-WP-002]
tags: []
---

## Requirement

Requirements:

- reconnect before/at 24h lifecycle;
- ping/pong compliance;
- combined streams configurable;
- trades;
- book deltas;
- mark/funding;
- OI polling;
- liquidations when available;
- error metrics.

## Acceptance

- connector reconnects before/at the 24h stream lifecycle limit;
- connector complies with ping/pong keepalive;
- combined streams are configurable;
- connector delivers trades, book deltas, mark/funding, and OI (polled);
- connector delivers liquidations when available from the venue;
- connector exposes error metrics.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-005-binance-connector]]
- **Code:**
    - `tools/record/binance_capture.py`
- **Outcomes:** [[OUT-2026-09-08-spec-binance-connector]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
