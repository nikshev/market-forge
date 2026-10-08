---
description: "Tasks for REQ-INFRA-006 — SignalNotary contract on Monad testnet"
---

# Tasks: SignalNotary contract on Monad testnet

**Input**: Design documents from `/specs/142-signal-notary-contract/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/signal-notary-abi.md

**Tests**: Written first. A task that makes something pass is preceded by the task that shows it failing for
the right reason (RED output goes into the implementation outcome note). The suite cannot be committed red
(the pre-commit hook runs it), so `tested` is recorded in the same commit as the implementation and the RED
output is what proves the order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 commit once · US2 resolve once · US3 owner only · US4 a deployment anyone can check

## Path Conventions

`contracts/` (Foundry project) · `tools/notary/` · `tests/contracts/` · `tests/tools/notary/` · `deployments/`

---

## Phase 1: Setup

- [X] T001 Create the Foundry project skeleton: `contracts/foundry.toml` (`solc_version = "0.8.28"`, `evm_version = "cancun"`, `src`, `test`, `out`, `cache`, no remappings), `contracts/test/utils/Vm.sol` (only the cheatcodes the suite uses: `prank`, `expectRevert`, `warp`, `recordLogs`/`getRecordedLogs`), and add `contracts/out/` and `contracts/cache/` to `.gitignore`
- [X] T002 Confirm on the installed Foundry (1.7.1) which signing mechanism keeps the key out of argv: encrypted keystore (`cast wallet import`, `--account`, `--password-file`) or a signer environment variable. Write the finding at the end of `research.md` R5. Import the existing deploy key into a keystore **without echoing it** (read from `/root/.monad/deployer.env`, never printed, never in argv), and record the keystore *account name* only. The keystore password lives in a mode-600 file outside the repository (`/root/.monad/keystore.pass`), referenced by path in configuration, never by value
- [X] T003 [P] Record **before**: `pytest --collect-only -q | tail -1` test count, and `cast balance` of the deploy account (the starting point for the cost of the deploy)

**Checkpoint**: `forge build` succeeds on an empty `src/`; the signing mechanism is known.

---

## Phase 2: User Stories 1–3 — the contract (offline)

**Goal**: FR-001…FR-009, SC-001, SC-002.

### Tests first (confirm RED for the right reason)

- [X] T004 [US1] [US2] [US3] `contracts/test/SignalNotary.t.sol`: the thirteen tests named in `contracts/signal-notary-abi.md` (`test_commit_emits_and_records`, `test_commit_twice_reverts_and_keeps_first`, `test_commit_zero_hash_reverts`, `test_resolve_emits_and_records` (outcomes 1, 2, 3), `test_resolve_uncommitted_reverts`, `test_resolve_twice_reverts_and_keeps_first`, `test_resolve_outcome_out_of_range_reverts` (0, 4, 255; the hash stays resolvable), `test_non_owner_cannot_commit`, `test_non_owner_cannot_resolve`, `test_constructor_rejects_zero_owner`, `test_owner_is_the_constructor_argument` (the getter FR-007 requires, which `verify.py` relies on), `test_value_is_rejected` (call with value and plain transfer), `test_block_time_is_not_bar_time` (warp the chain, commit an old `barTs`, the two fields differ and each is what was set))
- [X] T005 [US1] Add a stub `contracts/src/SignalNotary.sol` whose every function reverts `"unimplemented"` and run `forge test`: confirm the thirteen fail **by assertion, not by compile error**. Keep the output for the outcome note
- [X] T006 [P] [US1] `tests/contracts/test_signal_notary_suite.py`: module-scoped fixture runs `forge test --json` once in `contracts/`; **fails with the install command if `forge` is missing** (no skip); an explicit list of the thirteen expected names; one `@pytest.mark.trace("REQ-INFRA-006")` case per name asserting `status == "Success"`; one case asserting the run holds no test outside the list and the list is non-empty

### Implementation

- [X] T007 [US1] [US2] [US3] Implement `contracts/src/SignalNotary.sol` per `data-model.md`: storage `owner`, `commits`, `outcomes`; custom errors; `commit`, `resolve`, `commitOf`, `outcomeOf`; events; constructor rejects the zero address; no `receive`/`fallback`/payable; no function that deletes or overwrites. `forge test` all green, then once more with `forge test --offline` (solc already cached) to show the suite needs no network (SC-001)
- [X] T008 Mutation check of the Solidity suite (the repository's mutation sweep does not reach Solidity): for each guard — owner check, zero hash, duplicate commit, committed check on resolve, double resolve, outcome range, zero owner, `barTs` ≠ block time (store one in place of the other) — remove or break it, run `forge test`, confirm **exactly the test that names it goes red**, restore. Record the table in the implementation outcome. A guard whose removal leaves the suite green is a missing test: add it before moving on

**Checkpoint**: FR-001…FR-008 each have a test that fails without them; `make contracts-test` (T015) green.

---

## Phase 3: User Story 4 — tooling for a deployment anyone can check (offline parts)

**Goal**: FR-010, FR-012, FR-014, SC-003, SC-005.

### Tests first

- [X] T009 [P] [US4] `tests/tools/notary/test_chain.py` (`@pytest.mark.trace`): the argv the tool builds for `forge create` and `cast send` never contains a 64-hex-digit token nor the key's value; a chain-id mismatch between `MONAD_CHAIN_ID` and `cast chain-id` refuses before any transaction; the RPC URL and chain id come from the environment and a missing one is an error naming it
- [X] T010 [P] [US4] `tests/tools/notary/test_deploy.py` with a fake `cast`/`forge` on `PATH`: dry-run sends nothing and prints deployer, balance, chain id; `--broadcast` with a dirty `contracts/` tree refuses; a receipt with status 0, a created address that differs, on-chain code whose hash differs from `forge inspect … deployedBytecode`, or an `owner()` that differs each leave **no** `deployments/monad-testnet.json`; a clean read-back writes it, with every field in `data-model.md`
- [X] T011 [P] [US4] `tests/tools/notary/test_record.py`: if `deployments/monad-testnet.json` exists it has the full shape and `.env.example`'s `MONAD_NOTARY_ADDRESS` equals its `address`; if it does not exist, `MONAD_NOTARY_ADDRESS` is not set to a value in `.env.example` (FR-011, spec scenario 4.2). Plus: a scan of tracked files for the deploy account's key shape (64 hex after `0x`) outside test fixtures that are explicitly dummy values (FR-010, SC-005)

### Implementation

- [X] T012 [US4] `tools/notary/chain.py` (`# @trace: REQ-INFRA-006`): typed thin wrappers over `cast` (chain id, balance, receipt, code, call, send) and `forge create`; argv assembled in one place; secrets never logged
- [X] T013 [US4] `tools/notary/deploy.py` (`# @trace: REQ-INFRA-006`): the constructor's owner is `MONAD_NOTARY_OWNER` (documented configuration, Principle X), defaulting to the signer's address, and dry-run prints it; dry-run by default; `--broadcast` required to send; refuses a dirty `contracts/`; reads back receipt, address, code hash, `owner()`; writes the record **last**; prints the `.env.example` line to add
- [X] T014 [US4] `tools/notary/verify.py` (`# @trace: REQ-INFRA-006`): re-reads the recorded deployment from the chain; exit 1 naming the first mismatch (missing/failed receipt, different address, different code hash, different owner); a testnet that no longer resolves the address is reported as such
- [X] T015 [P] [US4] `Makefile`: `contracts-test` (`cd contracts && forge test`) and `notary-verify` (`$(PY) -m tools.notary.verify`); `.env.example`: documented `MONAD_NOTARY_OWNER` (defaults to the signer), `MONAD_RPC_URL`, `MONAD_CHAIN_ID`, `MONAD_EXPLORER_URL` (defaults from the network's published list), the signer account name, and **no value** for `MONAD_NOTARY_ADDRESS` yet; `docs/deployment.md`: a short "notary" section (what it is, how to deploy/verify, that the key lives in a keystore outside the repository)
- [X] T016 [P] `.github/workflows/ci.yml`: install Foundry (pinned to 1.7.1) before the test step, so the contract suite runs in the full gate (`make test` already collects `tests/contracts/`). Per CLAUDE.md "no check absent from both gates": confirm `tests/contracts/` is also collected by `make test-fast` (it needs no service), and say in the outcome that the workflow's green run is blocked by the unrelated MinIO failure

**Checkpoint**: `make lint && make typecheck && make test-fast` green; no deployment record exists yet.

- [X] T017 Commit Phases 2–3 (contract, tests, tooling; `status: tested`) with explicit paths, so `contracts/` is clean and committed before anything is deployed. The hook runs the suite (~7 minutes); do not edit the tree while it runs. No deployment record exists in this commit

---

## Phase 4: Deploy (the one outward-facing step)

**Goal**: FR-011, FR-013, SC-003, SC-004.

- [X] T018 [US4] Dry-run: `python -m tools.notary.deploy`; check chain id 10143, deployer, balance (≥ the cost estimate), and that `contracts/` is clean and committed. Do not proceed on a dirty tree
- [X] T019 [US4] `python -m tools.notary.deploy --broadcast`. Read the result back (the tool does); open the transaction on the explorer as a second, independent check. If any read-back step fails, **stop**: no record is written, nothing is claimed; diagnose, do not retry blindly
- [X] T020 [US4] `python -m tools.notary.verify` exits 0 against the public RPC
- [X] T021 [US4] `python -m tools.notary.smoke`: one real `commit`, read back the `Committed` event, one real `resolve`, read back `Resolved`; add the `smoke` block to the record only after both are read back (FR-013)
- [X] T022 [US4] Add `MONAD_NOTARY_ADDRESS=<address>` to `.env.example` (same value as the record); `test_record.py` now exercises its "both present and equal" branch

---

## Phase 5: Close-out

- [X] T023 Record **after**: test count, forge tests, the deploy's actual cost in MON (balance before − after), block time of the deployment, and the explorer links for deploy, commit and resolve transactions, in `vault/40-outcomes/OUT-<date>-implement-signal-notary-contract.md` together with the RED output (T005), the mutation table (T008) and what was *not* done (CI green run, timing claim of REQ-INFRA-007)
- [X] T024 `make graph` once, then `.venv/bin/python -m tools.trace.cli validate` (do not run `make validate` after `make graph`: it runs the suite twice). Set `status: implemented`; commit with explicit paths (pre-commit takes ~7 minutes; do not edit the tree while it runs)

---

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 commit | T004, T007 |
| FR-002 duplicate / zero hash | T004, T007, T008 |
| FR-003 resolve | T004, T007 |
| FR-004 resolve reverts | T004, T007, T008 |
| FR-005 immutability | T004 (both `…keeps_first` tests), T007 |
| FR-006 owner only, constructor argument | T004, T007, T008, T013 (`MONAD_NOTARY_OWNER`) |
| FR-007 two time fields, read access | T004 (`test_block_time_is_not_bar_time`, `test_owner_is_the_constructor_argument`), T007 |
| FR-008 no funds | T004 (`test_value_is_rejected`), T007 |
| FR-009 source, tests, deploy script in repo; offline tests | T001, T004, T007, T013 |
| FR-010 deploy script: env config, wrong chain refused, key never leaked | T002, T009, T011, T012, T013 |
| FR-011 deployed; recorded only after read-back | T010, T011, T013, T019, T022 |
| FR-012 verification script | T010, T014, T020 |
| FR-013 smoke commit + resolve | T021 |
| FR-014 traceability form | T006, T012–T014 (`# @trace:`), tests carry `@pytest.mark.trace` |
| SC-001 each behaviour has a test that fails without it; suite passes with no network | T007 (`--offline` run), T008 |
| SC-002 each named revert and the zero hash have their own test | T004 |
| SC-003 one command re-checks the deployment | T014, T015, T020 |
| SC-004 one commit and one resolve on the deployed address | T021, T023 |
| SC-005 key found zero times in tree and history | T011 (tracked-file scan), T023 (scan the diff of every commit this feature made for the 64-hex shape) |

## Dependencies

T001 → T004 → T005 → T007 → T008. T006 needs T004's names. T002 precedes T009, T012, T013. T009–T011 precede
T012–T014. T015/T016 are independent of each other. Phase 4 needs Phases 2–3 green **and committed** (T017)
(T013's clean-tree rule). T022 follows T019–T021. T023–T024 last.
