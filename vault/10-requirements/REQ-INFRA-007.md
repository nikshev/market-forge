---
id: REQ-INFRA-007
title: "Every final channel snapshot and every decision, including NO ALERT, is notarized after bar close"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: implemented
depends_on: [REQ-INFRA-006]
tags: [monad, notary, reproducibility]
hard_gated: false
---

## Requirement

After a bar closes, each **final** channel snapshot and each **decision** (including a decision not to
alert, `NO ALERT`) is hashed and committed through [[REQ-INFRA-006]].

The hashed record contains the snapshot or decision in its canonical encoding together with the **config
hash**, the **dataset version** (snapshot id) and the **code commit hash** — the three things
Principle XI says a result is reproducible from. Canonical encoding is the repository's existing one
(`experiments/hashing.py`'s `config_hash`; the lakehouse's content hash, [[ADR-053]]): a second encoding
would be a second definition of what the record *is*, and two drift.

The write is **asynchronous and never blocks the pipeline**: a chain outage delays notarization and is
visible, it does not delay a signal (the same rule [[REQ-WP-008]] states for Telegram).

Principle I is unaffected: the hash is computed from data already final at bar close, never earlier.

## Acceptance

- For one bar, the hash is reproducible: recomputing it from the stored snapshot, the config hash, the
  dataset snapshot id and the commit hash gives the committed value (a test, no network).
- Changing any one of the four inputs changes the hash (four tests).
- A `NO ALERT` decision is committed the same way as an alert.
- With the chain unreachable, signals are still produced and delivered, and an outbox of unsent commits
  is visible and drains when the chain returns (a test with a fake chain client).
- The interval from bar close to the commit's block time is measured on testnet and recorded; the
  product's claim is stated as that measured figure.
- Volume is sized in the plan: series × timeframes × bars a day, against the testnet's fee and rate
  limits, before the design commits to one transaction per decision.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-143-notarize-final-records]]
- **Tests:**
    - `tests/notary/test_notary_batcher.py::test_a_bar_close_that_is_not_a_whole_second_is_an_error_not_a_rounding`
    - `tests/notary/test_notary_batcher.py::test_a_batch_is_immutable_and_running_the_batcher_again_re_forms_nothing`
    - `tests/notary/test_notary_batcher.py::test_a_formed_batch_is_stored_and_its_records_leave_the_waiting_list`
    - `tests/notary/test_notary_batcher.py::test_a_record_belongs_to_at_most_one_batch_and_later_records_start_the_next`
    - `tests/notary/test_notary_batcher.py::test_a_window_that_has_not_elapsed_forms_nothing`
    - `tests/notary/test_notary_batcher.py::test_an_elapsed_window_forms_one_batch_over_everything_waiting_in_a_fixed_order`
    - `tests/notary/test_notary_batcher.py::test_an_empty_window_forms_nothing_and_costs_nothing`
    - `tests/notary/test_notary_batcher.py::test_the_cap_splits_a_backlog_into_batches_in_order`
    - `tests/notary/test_notary_batcher.py::test_unnotarizable_records_never_enter_a_batch`
    - `tests/notary/test_notary_chain.py::test_a_commit_is_read_at_the_requested_block_tag_and_zero_means_absent`
    - `tests/notary/test_notary_chain.py::test_a_foundry_keystore_decrypts_to_the_account_that_was_put_in`
    - `tests/notary/test_notary_chain.py::test_a_receipt_is_decoded_and_a_missing_one_is_none`
    - `tests/notary/test_notary_chain.py::test_a_root_the_chain_does_not_hold_has_no_evidence_and_costs_no_log_query`
    - `tests/notary/test_notary_chain.py::test_a_wrong_password_or_a_missing_file_fails_without_saying_either_secret`
    - `tests/notary/test_notary_chain.py::test_an_unreachable_node_is_a_chain_down`
    - `tests/notary/test_notary_chain.py::test_blocks_that_share_a_second_are_all_searched`
    - `tests/notary/test_notary_chain.py::test_every_way_the_node_can_fail_is_a_chain_down[http 500]`
    - `tests/notary/test_notary_chain.py::test_every_way_the_node_can_fail_is_a_chain_down[not json]`
    - `tests/notary/test_notary_chain.py::test_every_way_the_node_can_fail_is_a_chain_down[rpc error]`
    - `tests/notary/test_notary_chain.py::test_neither_the_key_nor_the_password_nor_a_provider_token_reaches_any_message`
    - `tests/notary/test_notary_chain.py::test_startup_refuses_a_wrong_chain_or_a_signer_that_is_not_the_owner`
    - `tests/notary/test_notary_chain.py::test_the_commit_calldata_is_what_cast_produces`
    - `tests/notary/test_notary_chain.py::test_the_commit_evidence_is_found_by_time_and_never_asks_for_more_than_a_hundred_blocks`
    - `tests/notary/test_notary_chain.py::test_the_http_transport_speaks_json_rpc`
    - `tests/notary/test_notary_chain.py::test_the_signed_transaction_recovers_to_the_signer_with_chain_nonce_and_tight_gas`
    - `tests/notary/test_notary_claim.py::test_no_user_facing_text_claims_a_commit_precedes_a_price_move`
    - `tests/notary/test_notary_claim.py::test_the_checker_flags_an_overclaim_and_lets_a_negation_through`
    - `tests/notary/test_notary_claim.py::test_the_checker_follows_a_sentence_across_a_line_break_but_not_across_a_full_stop`
    - `tests/notary/test_notary_claim.py::test_the_documentation_quotes_the_recorded_figure_or_says_it_has_none`
    - `tests/notary/test_notary_config.py::test_an_unset_commit_is_carried_as_absent_not_defaulted`
    - `tests/notary/test_notary_config.py::test_switched_on_it_needs_an_explicit_epoch`
    - `tests/notary/test_notary_config.py::test_the_epoch_is_an_instant_and_the_commit_comes_from_the_build`
    - `tests/notary/test_notary_config.py::test_the_notary_is_off_unless_it_is_switched_on`
    - `tests/notary/test_notary_context.py::test_a_component_nobody_classified_makes_the_context_unnotarizable_and_names_it`
    - `tests/notary/test_notary_context.py::test_a_config_value_that_cannot_be_hashed_makes_it_unnotarizable_never_skipped`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides0-commit]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides1-commit]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides2-commit]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides3-commit]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides4-dirty]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides5-dirty]`
    - `tests/notary/test_notary_context.py::test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason[overrides6-dirty]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.band_sigmas]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.bands]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.lookback]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.min_window_bars]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.quantile_high]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[channel.quantile_low]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[detector.min_distance]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.expiry_bars]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.min_quality]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.opens]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.overshoot_tolerance]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.slope_threshold]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.zone_lower]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.zone_middle]`
    - `tests/notary/test_notary_context.py::test_changing_any_configuration_field_changes_the_config_hash[machine.zone_upper]`
    - `tests/notary/test_notary_context.py::test_every_field_of_every_component_is_classified_as_configuration_or_as_state`
    - `tests/notary/test_notary_context.py::test_the_config_names_the_class_of_each_component`
    - `tests/notary/test_notary_context.py::test_the_dataset_reference_is_the_repositorys_over_the_pinned_bars_snapshot`
    - `tests/notary/test_notary_context.py::test_the_gap_threshold_setting_is_part_of_the_config`
    - `tests/notary/test_notary_context.py::test_the_machines_state_is_not_part_of_the_config`
    - `tests/notary/test_notary_latency.py::test_a_sample_below_the_success_criterion_is_labelled_insufficient_not_reported_as_a_result`
    - `tests/notary/test_notary_latency.py::test_a_sample_that_meets_the_criterion_says_so`
    - `tests/notary/test_notary_latency.py::test_latency_is_per_record_from_its_own_bar_close_not_per_batch`
    - `tests/notary/test_notary_latency.py::test_only_confirmed_batches_count_and_the_window_filters_by_the_chains_time`
    - `tests/notary/test_notary_latency.py::test_the_latency_command_prints_the_report_as_json`
    - `tests/notary/test_notary_latency.py::test_the_percentile_is_nearest_rank_and_never_interpolated`
    - `tests/notary/test_notary_main.py::test_a_malformed_value_names_its_variable[CHANNELFLOW_NOTARY_BATCH_WINDOW-soon]`
    - `tests/notary/test_notary_main.py::test_a_malformed_value_names_its_variable[CHANNELFLOW_NOTARY_GAS_MARGIN-0.9]`
    - `tests/notary/test_notary_main.py::test_a_malformed_value_names_its_variable[CHANNELFLOW_NOTARY_MAX_BATCH-0]`
    - `tests/notary/test_notary_main.py::test_a_malformed_value_names_its_variable[MONAD_NOTARY_ADDRESS-not-an-address]`
    - `tests/notary/test_notary_main.py::test_a_malformed_value_names_its_variable[MONAD_NOTARY_DEPLOY_BLOCK-yesterday]`
    - `tests/notary/test_notary_main.py::test_every_missing_required_variable_is_named[CHANNELFLOW_NOTARY_KEYSTORE]`
    - `tests/notary/test_notary_main.py::test_every_missing_required_variable_is_named[CHANNELFLOW_NOTARY_PASSWORD_FILE]`
    - `tests/notary/test_notary_main.py::test_every_missing_required_variable_is_named[MONAD_NOTARY_ADDRESS]`
    - `tests/notary/test_notary_main.py::test_every_missing_required_variable_is_named[MONAD_NOTARY_DEPLOY_BLOCK]`
    - `tests/notary/test_notary_main.py::test_overrides_use_the_same_duration_grammar_as_the_other_loops`
    - `tests/notary/test_notary_main.py::test_the_defaults_are_the_planned_ones_and_units_are_converted`
    - `tests/notary/test_notary_main.py::test_the_gauges_are_exposed_with_the_outbox_numbers`
    - `tests/notary/test_notary_main.py::test_the_loop_continues_after_a_tick_that_raises`
    - `tests/notary/test_notary_main.py::test_the_metrics_survive_an_unreachable_chain`
    - `tests/notary/test_notary_main.py::test_the_outbox_listing_says_what_waits_and_why`
    - `tests/notary/test_notary_pass.py::test_a_pass_without_a_usable_commit_stores_unnotarizable_records_and_still_runs`
    - `tests/notary/test_notary_pass.py::test_a_real_pass_through_an_outage_and_back_every_record_is_committed_once_and_provable`
    - `tests/notary/test_notary_pass.py::test_a_registration_that_fails_does_not_change_or_stop_the_pass`
    - `tests/notary/test_notary_pass.py::test_a_second_cycle_registers_nothing_new`
    - `tests/notary/test_notary_pass.py::test_every_read_of_the_pass_uses_the_one_pinned_bars_snapshot`
    - `tests/notary/test_notary_pass.py::test_the_notary_adds_one_read_to_a_pass_and_no_read_of_any_other_table`
    - `tests/notary/test_notary_pass.py::test_the_pass_writes_exactly_the_same_with_the_notary_attached`
    - `tests/notary/test_notary_records.py::test_a_decision_is_identified_by_its_signal_and_its_position_in_the_history`
    - `tests/notary/test_notary_records.py::test_a_longer_history_extends_the_same_decisions_and_never_renumbers_them`
    - `tests/notary/test_notary_records.py::test_a_snapshot_that_saw_the_future_is_refused_even_if_built_around_the_model`
    - `tests/notary/test_notary_records.py::test_a_snapshot_whose_bar_is_not_final_is_refused`
    - `tests/notary/test_notary_records.py::test_a_snapshots_canonical_bytes_are_the_lakehouses_own_row_encoding`
    - `tests/notary/test_notary_records.py::test_a_suppression_is_a_decision_with_the_reason_the_gate_recorded`
    - `tests/notary/test_notary_records.py::test_expiring_without_ever_alerting_is_a_no_alert_decision_carrying_its_reason`
    - `tests/notary/test_notary_records.py::test_only_a_suppressed_audit_record_is_a_suppression`
    - `tests/notary/test_notary_records.py::test_reaching_alerted_is_an_alert_and_a_later_invalidation_is_not_a_no_alert`
    - `tests/notary/test_notary_registrar.py::test_a_bar_that_is_not_final_is_refused_and_counted_never_registered`
    - `tests/notary/test_notary_registrar.py::test_a_crash_between_the_lakehouse_write_and_the_registration_loses_nothing`
    - `tests/notary/test_notary_registrar.py::test_a_pass_registers_each_snapshot_once_and_the_hash_can_be_recomputed`
    - `tests/notary/test_notary_registrar.py::test_a_second_pass_over_the_same_data_registers_nothing`
    - `tests/notary/test_notary_registrar.py::test_a_terminal_outcome_the_signals_table_never_received_is_still_registered`
    - `tests/notary/test_notary_registrar.py::test_an_unnotarizable_context_stores_the_record_with_the_reason_and_no_hash`
    - `tests/notary/test_notary_registrar.py::test_every_transition_of_every_candidate_is_registered_once`
    - `tests/notary/test_notary_registrar.py::test_records_before_the_epoch_are_not_registered`
    - `tests/notary/test_notary_scheme.py::test_a_value_cannot_be_shifted_across_a_frame_boundary`
    - `tests/notary/test_notary_scheme.py::test_an_empty_record_differs_from_a_missing_one_and_from_another_empty_field`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[code_commit-decision]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[code_commit-snapshot]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[config_hash-decision]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[config_hash-snapshot]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[dataset_ref-decision]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[dataset_ref-snapshot]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[record-decision]`
    - `tests/notary/test_notary_scheme.py::test_changing_any_one_of_the_four_inputs_changes_the_hash[record-snapshot]`
    - `tests/notary/test_notary_scheme.py::test_the_envelope_is_the_one_the_specification_describes`
    - `tests/notary/test_notary_scheme.py::test_the_format_is_pinned_by_a_literal_vector`
    - `tests/notary/test_notary_scheme.py::test_the_hash_is_a_function_of_its_inputs_alone`
    - `tests/notary/test_notary_scheme.py::test_the_kind_and_the_scheme_version_are_part_of_the_hash`
    - `tests/notary/test_notary_submitter.py::test_a_balance_under_the_floor_holds_the_batch_once_and_sends_nothing`
    - `tests/notary/test_notary_submitter.py::test_a_commit_we_sent_is_confirmed_from_its_receipt_without_searching_logs`
    - `tests/notary/test_notary_submitter.py::test_a_failure_after_the_chain_accepted_the_transaction_is_reconciled_not_resent`
    - `tests/notary/test_notary_submitter.py::test_a_formed_batch_is_sent_once_and_confirmed_from_the_chain`
    - `tests/notary/test_notary_submitter.py::test_a_gas_price_over_the_ceiling_holds_the_batch`
    - `tests/notary/test_notary_submitter.py::test_a_log_search_that_the_node_refuses_leaves_the_batch_pending_not_lost`
    - `tests/notary/test_notary_submitter.py::test_a_process_that_died_before_recording_anything_finds_its_root_on_chain`
    - `tests/notary/test_notary_submitter.py::test_a_record_registered_while_the_summary_is_computed_does_not_break_it`
    - `tests/notary/test_notary_submitter.py::test_a_reverted_transaction_is_a_failure_and_is_retried`
    - `tests/notary/test_notary_submitter.py::test_a_transaction_still_in_flight_is_not_sent_again_before_its_timeout`
    - `tests/notary/test_notary_submitter.py::test_a_transaction_that_was_mined_as_a_revert_after_we_stopped_looking_is_noticed`
    - `tests/notary/test_notary_submitter.py::test_an_unexpected_error_in_one_tick_does_not_end_the_loop`
    - `tests/notary/test_notary_submitter.py::test_an_unreachable_chain_loses_nothing_and_the_same_root_is_retried`
    - `tests/notary/test_notary_submitter.py::test_batches_are_sent_in_order_and_a_held_one_holds_those_behind_it`
    - `tests/notary/test_notary_submitter.py::test_confirmed_means_finalized_not_merely_visible`
    - `tests/notary/test_notary_submitter.py::test_leaves_written_before_a_crash_are_completed_into_a_batch_and_sent`
    - `tests/notary/test_notary_submitter.py::test_one_batch_that_cannot_be_sent_holds_every_batch_behind_it`
    - `tests/notary/test_notary_submitter.py::test_orphaned_leaves_that_do_not_hash_to_their_root_are_not_turned_into_a_batch`
    - `tests/notary/test_notary_submitter.py::test_the_outbox_is_visible_while_the_chain_is_down_and_drains_when_it_returns`
    - `tests/notary/test_notary_submitter.py::test_the_summary_reads_the_records_table_exactly_once`
    - `tests/notary/test_notary_tables.py::test_a_batchs_state_is_its_latest_event`
    - `tests/notary/test_notary_tables.py::test_registered_ids_and_unbatched_records_follow_the_leaves`
    - `tests/notary/test_notary_tree.py::test_a_proof_fails_for_a_flipped_leaf_path_index_or_size`
    - `tests/notary/test_notary_tree.py::test_an_interior_node_cannot_pass_as_a_leaf`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[10]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[11]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[12]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[13]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[14]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[15]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[16]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[17]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[1]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[2]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[3]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[4]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[5]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[6]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[7]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[8]`
    - `tests/notary/test_notary_tree.py::test_every_leaf_of_every_size_has_the_rfc_path_and_verifies[9]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[10]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[11]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[12]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[13]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[14]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[15]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[16]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[17]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[1]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[2]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[3]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[4]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[5]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[6]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[7]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[8]`
    - `tests/notary/test_notary_tree.py::test_the_root_equals_the_independent_implementation[9]`
    - `tests/notary/test_notary_tree.py::test_the_tree_is_a_function_of_the_ordered_list_and_an_empty_tree_is_refused`
    - `tests/notary/test_notary_verify.py::test_a_bundle_verifies_with_nothing_but_the_bundle_and_the_chain`
    - `tests/notary/test_notary_verify.py::test_a_notarized_record_verifies_with_its_block_its_transaction_and_its_latency[decision]`
    - `tests/notary/test_notary_verify.py::test_a_notarized_record_verifies_with_its_block_its_transaction_and_its_latency[snapshot]`
    - `tests/notary/test_notary_verify.py::test_a_record_in_an_unconfirmed_batch_is_pending_never_committed`
    - `tests/notary/test_notary_verify.py::test_a_record_not_yet_in_any_batch_is_pending`
    - `tests/notary/test_notary_verify.py::test_a_root_the_chain_does_not_have_is_not_committed`
    - `tests/notary/test_notary_verify.py::test_an_unknown_record_and_an_unnotarizable_one_are_not_committed`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[commit]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[config]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[dataset]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[index]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[path]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[record]`
    - `tests/notary/test_notary_verify.py::test_any_altered_field_is_not_committed_and_says_why[root]`
    - `tests/notary/test_notary_verify.py::test_export_then_bundle_round_trips_through_a_file_with_no_lakehouse`
    - `tests/notary/test_notary_verify.py::test_the_bar_close_is_read_from_the_records_own_bytes`
    - `tests/notary/test_notary_verify.py::test_the_check_command_exits_nonzero_for_pending_and_for_not_committed`
    - `tests/notary/test_notary_verify.py::test_the_check_command_reports_committed_with_the_block_and_the_honest_claim`
    - `tests/unit/deploy/test_notary_compose.py::test_no_environment_value_in_the_compose_file_is_or_names_a_key`
    - `tests/unit/deploy/test_notary_compose.py::test_only_the_notary_is_given_the_keystore_and_its_password`
    - `tests/unit/deploy/test_notary_compose.py::test_the_build_info_target_prints_the_commit_and_the_dirty_flag_but_never_the_epoch`
    - `tests/unit/deploy/test_notary_compose.py::test_the_commit_is_baked_in_at_build_for_the_worker_and_the_notary`
    - `tests/unit/deploy/test_notary_compose.py::test_the_worker_holds_no_key_and_no_chain_setting`
    - `tests/unit/deploy/test_notary_compose.py::test_there_is_a_notary_service_that_starts_only_when_asked_for`
- **Code:**
    - `src/channelflow/notary/__init__.py`
    - `src/channelflow/notary/batcher.py`
    - `src/channelflow/notary/chain.py`
    - `src/channelflow/notary/config.py`
    - `src/channelflow/notary/context.py`
    - `src/channelflow/notary/latency.py`
    - `src/channelflow/notary/main.py`
    - `src/channelflow/notary/records.py`
    - `src/channelflow/notary/registrar.py`
    - `src/channelflow/notary/scheme.py`
    - `src/channelflow/notary/submitter.py`
    - `src/channelflow/notary/tables.py`
    - `src/channelflow/notary/verify.py`
    - `src/channelflow/pipeline/channel_main.py`
- **Outcomes:** [[OUT-2026-10-08-implement-notarize-final-records]], [[OUT-2026-10-08-plan-notarize-final-records]], [[OUT-2026-10-08-spec-notarize-final-records]], [[OUT-2026-10-08-tasks-notarize-final-records]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
