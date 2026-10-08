---
id: REQ-INFRA-006
title: "SignalNotary: a minimal contract on Monad testnet that notarizes signal hashes"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: implemented
depends_on: []
tags: [monad, notary, onchain]
hard_gated: false
---

## Requirement

**Why this exists.** The product's central promise is "signals are not repainted". While the signal
journal sits in a private database that is only words. A hash of each decision written to a public
chain makes it checkable by anyone, so long as what is hashed is exactly what was shown.

The contract is deliberately minimal for the MVP:

- `commit(bytes32 hash, uint64 barTs)` records that `hash` was committed, with the bar's close time,
  and emits `Committed(hash, barTs, committer)`.
- `resolve(bytes32 hash, uint8 outcome)` records the outcome of a previously committed hash and emits
  `Resolved(hash, outcome)`. Outcomes: `1` target hit, `2` invalidated, `3` expired.
- A hash can be committed once and resolved once; neither can be changed afterwards.
- Only the deployer's configured account may write (the contract is a notary of this system's own
  decisions, not a public registry).

**What this does and does not prove.** The block timestamp proves the hash existed no later than that
block. It does *not* by itself prove the signal preceded a price move: that holds only if the commit
lands before the move, so the claim the product may make is "committed within N seconds of bar
close", with N measured, not "before the move".

## Acceptance

- The contract source, its tests and a deploy script are in the repository.
- Tests (no network) show: a commit emits its event; a second commit of the same hash reverts; a resolve
  of an uncommitted hash reverts; a second resolve reverts; a non-owner write reverts; `outcome`
  outside `1..3` reverts.
- The contract is deployed to **Monad testnet** and its address and deployment transaction are recorded
  in the outcome note and in `.env.example` as a documented variable. This is the evidence for the
  hackathon submission's *Live product* field.
- The address is recorded **only after** a transaction has been read back from the chain; nothing in the
  repository claims a deployment that did not happen.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-142-signal-notary-contract]]
- **Tests:**
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_run_holds_no_test_outside_the_list`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_block_time_is_not_bar_time]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_emits_and_records]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_twice_reverts_and_keeps_first]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_zero_hash_reverts]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_constructor_rejects_zero_owner]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_non_owner_cannot_commit]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_non_owner_cannot_resolve]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_owner_is_the_constructor_argument]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_emits_and_records]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_outcome_out_of_range_reverts]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_twice_reverts_and_keeps_first]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_uncommitted_reverts]`
    - `tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_value_is_rejected]`
    - `tests/tools/notary/test_notary_chain.py::test_a_chain_id_other_than_the_configured_one_is_refused_before_any_transaction`
    - `tests/tools/notary/test_notary_chain.py::test_a_key_in_the_environment_is_never_read_into_the_configuration`
    - `tests/tools/notary/test_notary_chain.py::test_a_missing_signer_account_is_an_error_that_names_the_variable`
    - `tests/tools/notary/test_notary_chain.py::test_no_command_line_the_chain_builds_carries_a_raw_key`
    - `tests/tools/notary/test_notary_chain.py::test_signing_is_an_account_and_a_password_file_and_nothing_else`
    - `tests/tools/notary/test_notary_chain.py::test_the_network_comes_from_the_environment_with_the_published_testnet_as_default`
    - `tests/tools/notary/test_notary_deploy.py::test_a_balance_of_zero_refuses_to_broadcast`
    - `tests/tools/notary/test_notary_deploy.py::test_a_clean_read_back_writes_the_record_with_every_field`
    - `tests/tools/notary/test_notary_deploy.py::test_a_dirty_contracts_tree_refuses_to_broadcast_but_not_to_dry_run`
    - `tests/tools/notary/test_notary_deploy.py::test_a_dry_run_sends_nothing_and_writes_no_record`
    - `tests/tools/notary/test_notary_deploy.py::test_a_failed_read_back_leaves_no_record[damage0-status]`
    - `tests/tools/notary/test_notary_deploy.py::test_a_failed_read_back_leaves_no_record[damage1-address]`
    - `tests/tools/notary/test_notary_deploy.py::test_a_failed_read_back_leaves_no_record[damage2-code]`
    - `tests/tools/notary/test_notary_deploy.py::test_a_failed_read_back_leaves_no_record[damage3-owner]`
    - `tests/tools/notary/test_notary_deploy.py::test_a_failed_read_back_leaves_no_record[damage4-sender]`
    - `tests/tools/notary/test_notary_deploy.py::test_smoke_commits_and_resolves_and_records_both_transactions_after_reading_them_back`
    - `tests/tools/notary/test_notary_deploy.py::test_smoke_records_nothing_when_a_read_back_disagrees[break_commit_event]`
    - `tests/tools/notary/test_notary_deploy.py::test_smoke_records_nothing_when_a_read_back_disagrees[break_commit_read]`
    - `tests/tools/notary/test_notary_deploy.py::test_the_owner_is_configuration_and_defaults_to_the_signer`
    - `tests/tools/notary/test_notary_deploy.py::test_the_wrong_chain_is_refused_before_anything_is_sent`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage0-status]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage1-address]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage2-code]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage3-compiled]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage4-owner]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_fails_loudly_and_says_which_check_differs[damage5-chain]`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_passes_for_a_deployment_that_is_what_the_record_says`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_reports_a_missing_receipt_as_not_deployed_never_as_success`
    - `tests/tools/notary/test_notary_deploy.py::test_verify_without_a_record_says_nothing_was_deployed`
    - `tests/tools/notary/test_notary_record.py::test_env_example_documents_the_monad_variables`
    - `tests/tools/notary/test_notary_record.py::test_no_tracked_file_holds_something_shaped_like_a_private_key`
    - `tests/tools/notary/test_notary_record.py::test_the_record_and_env_example_agree_or_both_are_absent`
    - `tests/unit/deploy/test_section_34.py::test_a_public_address_is_allowed_in_the_template_and_a_private_key_is_not`
- **Code:**
    - `tools/notary/chain.py`
    - `tools/notary/deploy.py`
    - `tools/notary/record.py`
    - `tools/notary/smoke.py`
    - `tools/notary/verify.py`
- **Outcomes:** [[OUT-2026-10-08-implement-signal-notary-contract]], [[OUT-2026-10-08-plan-signal-notary-contract]], [[OUT-2026-10-08-spec-signal-notary-contract]], [[OUT-2026-10-08-tasks-signal-notary-contract]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

- Needs, from the user: the account that deploys (key held outside the repository), testnet funds, and the
  RPC endpoint. None is requested or stored here. Deployment is an outward-facing step and waits for them.
- Deadline given by the user: **2026-10-14**.
