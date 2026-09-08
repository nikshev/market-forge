---
id: REQ-WP-008
title: Telegram
type: work-package
prd_ref: "WP-008 Telegram"
prd_lines: "6987-6994"
phase: null
status: specified
depends_on: ["REQ-WP-007"]
tags: []
---

## Requirement

- format alert;
- inline deep-link button;
- dedupe;
- retry;
- delivery audit.

## Acceptance

- alert message is formatted;
- alert carries an inline deep-link button;
- duplicate alerts are deduped;
- delivery is retried on failure;
- delivery is audited.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-012-telegram-alerting]]
- **Outcomes:** [[OUT-2026-09-08-spec-telegram-alerting]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
