---
id: REQ-US-002
title: Open exact chart state
type: user-story
prd_ref: "US-002 — Open exact chart state"
prd_lines: "255-258"
phase: null
status: implemented
depends_on: ["REQ-WP-008", "REQ-WP-009"]
tags: []
---

## Requirement

As a user, I want to click a button in Telegram and open the chart at exactly the signal's timestamp, with all active overlays.

## Acceptance

- clicking the Telegram button opens the chart at exactly the signal's timestamp;
- all overlays active at signal time are restored.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-027-deep-link-overlays]]
- **Tests:**
    - `tests/unit/alerting/test_deep_link_overlays.py::test_an_alert_declaring_nothing_omits_the_parameter`
    - `tests/unit/alerting/test_deep_link_overlays.py::test_an_overlay_the_prd_does_not_list_is_refused`
    - `tests/unit/alerting/test_deep_link_overlays.py::test_the_instant_and_the_signal_id_are_still_in_the_link`
    - `tests/unit/alerting/test_deep_link_overlays.py::test_the_link_names_the_overlays_that_were_active`
    - `tests/unit/alerting/test_deep_link_overlays.py::test_the_overlay_order_is_stable`
    - `tests/unit/alerting/test_deep_link_overlays.py::test_the_overlay_vocabulary_is_the_prds_own_list`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/__tests__/deepLinkOverlays.test.tsx`
    - `apps/web/src/__tests__/overlays.test.ts`
    - `apps/web/src/overlays.ts`
    - `src/channelflow/alerting/__init__.py`
    - `src/channelflow/alerting/overlays.py`
- **Outcomes:** [[OUT-2026-09-09-implement-deep-link-overlays]], [[OUT-2026-09-09-plan-deep-link-overlays]], [[OUT-2026-09-09-spec-deep-link-overlays]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
