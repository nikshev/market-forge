---
id: REQ-WP-014
title: EVM connector
type: work-package
prd_ref: "WP-014 EVM connector"
prd_lines: "7033-7040"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

- logs;
- finality;
- reorg;
- ABI decoder;
- RPC health.

## Acceptance

- raw logs are ingested;
- a finality policy is applied;
- reorgs are handled;
- an ABI decoder is available;
- RPC health is reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-020-evm-connector]]
- **Tests:**
    - `tests/unit/chain/test_decoders.py::test_a_log_before_the_deployment_range_is_not_covered`
    - `tests/unit/chain/test_decoders.py::test_a_log_with_no_registry_entry_produces_no_event_but_keeps_the_record`
    - `tests/unit/chain/test_decoders.py::test_a_mismatched_abi_hash_fails_closed`
    - `tests/unit/chain/test_decoders.py::test_a_registered_decoder_handles_its_log`
    - `tests/unit/chain/test_decoders.py::test_deployment_ranges_select_between_decoder_versions`
    - `tests/unit/chain/test_decoders.py::test_the_chain_package_cannot_consult_a_clock_or_open_a_socket`
    - `tests/unit/chain/test_ledger.py::test_a_backtest_cannot_read_earlier_than_the_live_system_could`
    - `tests/unit/chain/test_ledger.py::test_a_finalized_block_cannot_be_reorganised`
    - `tests/unit/chain/test_ledger.py::test_a_read_before_the_reorg_still_returns_the_record`
    - `tests/unit/chain/test_ledger.py::test_a_record_is_immutable`
    - `tests/unit/chain/test_ledger.py::test_a_record_is_invisible_until_it_was_available`
    - `tests/unit/chain/test_ledger.py::test_a_reorg_of_an_unseen_block_is_recorded_and_harmless`
    - `tests/unit/chain/test_ledger.py::test_a_reorg_orphans_a_record_and_never_edits_it`
    - `tests/unit/chain/test_ledger.py::test_a_safe_only_read_excludes_what_had_not_reached_it`
    - `tests/unit/chain/test_ledger.py::test_availability_is_never_before_observation`
    - `tests/unit/chain/test_ledger.py::test_finality_advances_at_the_configured_depths`
    - `tests/unit/chain/test_ledger.py::test_finality_never_regresses`
    - `tests/unit/chain/test_ledger.py::test_records_are_returned_in_chain_order`
    - `tests/unit/chain/test_providers.py::test_a_cooldown_expires`
    - `tests/unit/chain/test_providers.py::test_a_cross_provider_disagreement_is_reported_not_resolved`
    - `tests/unit/chain/test_providers.py::test_agreement_reports_nothing`
    - `tests/unit/chain/test_providers.py::test_an_empty_pool_refuses`
    - `tests/unit/chain/test_providers.py::test_an_error_storm_puts_a_provider_in_cooldown`
    - `tests/unit/chain/test_providers.py::test_health_reports_latency_errors_and_gaps`
    - `tests/unit/chain/test_providers.py::test_no_healthy_provider_refuses`
    - `tests/unit/chain/test_providers.py::test_the_fastest_healthy_provider_is_chosen`
    - `tests/unit/chain/test_providers.py::test_the_rates_are_windowed_not_lifetime`
- **Code:**
    - `src/channelflow/chain/__init__.py`
    - `src/channelflow/chain/decoders.py`
    - `src/channelflow/chain/ledger.py`
    - `src/channelflow/chain/providers.py`
    - `src/channelflow/chain/records.py`
- **Outcomes:** [[OUT-2026-09-08-implement-evm-connector]], [[OUT-2026-09-08-plan-evm-connector]], [[OUT-2026-09-08-spec-evm-connector]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
