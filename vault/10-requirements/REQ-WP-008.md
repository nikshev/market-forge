---
id: REQ-WP-008
title: Telegram
type: work-package
prd_ref: "WP-008 Telegram"
prd_lines: "6987-6994"
phase: null
status: implemented
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
- **Tests:**
    - `tests/unit/alerting/test_dedupe.py::test_a_cooldown_plus_a_new_touch_allows_a_new_alert`
    - `tests/unit/alerting/test_dedupe.py::test_a_new_touch_before_the_cooldown_is_refused`
    - `tests/unit/alerting/test_dedupe.py::test_a_phase_change_allows_a_new_alert`
    - `tests/unit/alerting/test_dedupe.py::test_an_elapsed_cooldown_alone_does_not_allow_a_new_alert`
    - `tests/unit/alerting/test_dedupe.py::test_the_cooldown_is_configurable`
    - `tests/unit/alerting/test_dedupe.py::test_the_first_alert_for_a_setup_is_allowed`
    - `tests/unit/alerting/test_dedupe.py::test_the_same_state_offered_again_is_refused`
    - `tests/unit/alerting/test_dedupe.py::test_two_symbols_do_not_suppress_each_other`
    - `tests/unit/alerting/test_dispatch.py::test_a_first_time_success_is_delivered_and_audited`
    - `tests/unit/alerting/test_dispatch.py::test_a_throwing_transport_never_reaches_the_caller`
    - `tests/unit/alerting/test_dispatch.py::test_a_transport_failing_twice_delivers_on_the_third_attempt`
    - `tests/unit/alerting/test_dispatch.py::test_a_transport_that_always_fails_dead_letters`
    - `tests/unit/alerting/test_dispatch.py::test_an_unexpected_response_is_treated_as_a_failure`
    - `tests/unit/alerting/test_dispatch.py::test_backoff_delays_strictly_increase`
    - `tests/unit/alerting/test_dispatch.py::test_the_engine_keeps_going_after_a_dead_letter`
    - `tests/unit/alerting/test_dispatch.py::test_the_message_and_the_link_both_reach_the_transport`
    - `tests/unit/alerting/test_render.py::test_a_section_with_no_data_is_absent_by_heading`
    - `tests/unit/alerting/test_render.py::test_an_alert_without_a_chart_base_is_refused`
    - `tests/unit/alerting/test_render.py::test_no_placeholder_is_substituted_for_a_missing_block`
    - `tests/unit/alerting/test_render.py::test_rendering_is_deterministic`
    - `tests/unit/alerting/test_render.py::test_the_chart_host_is_configured_not_hard_coded`
    - `tests/unit/alerting/test_render.py::test_the_deep_link_follows_the_documented_format`
    - `tests/unit/alerting/test_render.py::test_the_full_message_matches_expected_output`
    - `tests/unit/alerting/test_render.py::test_the_signal_id_differs_for_a_different_candidate`
    - `tests/unit/alerting/test_render.py::test_the_signal_id_is_the_same_for_the_same_candidate`
    - `tests/unit/alerting/test_render.py::test_the_signal_id_is_uuid_shaped`
    - `tests/unit/alerting/test_safety.py::test_a_fresh_book_lets_the_alert_through`
    - `tests/unit/alerting/test_safety.py::test_a_stale_book_suppresses_the_alert`
    - `tests/unit/alerting/test_safety.py::test_a_suppression_is_visible_in_the_audit`
    - `tests/unit/alerting/test_safety.py::test_an_invalid_book_suppresses_the_alert`
    - `tests/unit/alerting/test_safety.py::test_no_credential_appears_in_the_package_or_in_a_message`
    - `tests/unit/alerting/test_safety.py::test_the_alerting_package_has_no_clock_and_no_http_client`
    - `tests/unit/alerting/test_safety.py::test_the_tolerance_is_configurable`
- **Code:**
    - `src/channelflow/alerting/__init__.py`
    - `src/channelflow/alerting/dedupe.py`
    - `src/channelflow/alerting/dispatch.py`
    - `src/channelflow/alerting/gate.py`
    - `src/channelflow/alerting/models.py`
    - `src/channelflow/alerting/render.py`
- **Outcomes:** [[OUT-2026-09-08-implement-telegram-alerting]], [[OUT-2026-09-08-plan-telegram-alerting]], [[OUT-2026-09-08-spec-telegram-alerting]], [[OUT-2026-09-08-tasks-telegram-alerting]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
