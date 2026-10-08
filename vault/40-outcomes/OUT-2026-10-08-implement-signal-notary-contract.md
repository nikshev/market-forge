---
id: OUT-2026-10-08-implement-signal-notary-contract
step: implement
records: [REQ-INFRA-006]
commit: null
---

## What was done

Implemented [[REQ-INFRA-006]] in two stages, with the deployment between them (tasks T001–T024 in
`specs/142-signal-notary-contract/tasks.md`).

**Stage 1 -- contract, offline suite and tooling (T001–T017), `status: tested`.** `contracts/` (Foundry,
solc 0.8.28, no libraries), `SignalNotary.sol`, thirteen Solidity tests, `tests/contracts/` (the pytest driver
that makes them visible to the trace graph), and `tools/notary/` (`chain`, `deploy`, `verify`, `smoke`,
`record`) with thirty-two tests against an in-memory chain.

**Stage 2 -- the deployment (T018–T024):** see "Deployment" below; the record, `.env.example` and the status moved in the commit that follows the `tested` one.

### RED, before any implementation (T005)

A stub `SignalNotary.sol` whose functions revert `"unimplemented"` was compiled and the thirteen tests run:
`forge test` -> **1 passed, 12 failed**, every failure an assertion or an unexpected revert, none a compile
error:

```
[FAIL: Error != expected error: unimplemented != NotCommitted()] test_resolve_uncommitted_reverts() (gas: 9386)
[FAIL: Error != expected error: unimplemented != NotOwner()] test_non_owner_cannot_commit() (gas: 9918)
[FAIL: Error != expected error: unimplemented != ZeroHash()] test_commit_zero_hash_reverts() (gas: 9434)
[FAIL: next call did not revert as expected] test_constructor_rejects_zero_owner() (gas: 263088)
[FAIL: panic: assertion failed (0x01)] test_owner_is_the_constructor_argument() (gas: 261079)
[FAIL: unimplemented] test_block_time_is_not_bar_time() (gas: 9497)
[FAIL: unimplemented] test_commit_emits_and_records() (gas: 9855)
[FAIL: unimplemented] test_commit_twice_reverts_and_keeps_first() (gas: 9541)
[FAIL: unimplemented] test_non_owner_cannot_resolve() (gas: 6386)
[FAIL: unimplemented] test_resolve_emits_and_records() (gas: 6932)
[FAIL: unimplemented] test_resolve_outcome_out_of_range_reverts() (gas: 6407)
[FAIL: unimplemented] test_resolve_twice_reverts_and_keeps_first() (gas: 6452)
[PASS] test_value_is_rejected() (gas: 25507)
Suite result: FAILED. 1 passed; 12 failed; 0 skipped; finished in 11.85ms (1.34ms CPU time)
```

The one that passed, `test_value_is_rejected`, passed against the stub because the stub has no payable
function either; it is a regression guard, and the mutation table below shows it goes red when the contract
*does* accept value.

The pytest driver against the same stub (`pytest tests/contracts`):

```
E       AssertionError: test_owner_is_the_constructor_argument: Failure -- panic: assertion failed (0x01)
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_emits_and_records]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_twice_reverts_and_keeps_first]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_commit_zero_hash_reverts]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_emits_and_records]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_uncommitted_reverts]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_twice_reverts_and_keeps_first]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_resolve_outcome_out_of_range_reverts]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_non_owner_cannot_commit]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_non_owner_cannot_resolve]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_constructor_rejects_zero_owner]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_owner_is_the_constructor_argument]
FAILED tests/contracts/test_signal_notary_suite.py::test_the_forge_test_exists_and_passes[test_block_time_is_not_bar_time]
12 failed, 2 passed in 0.18s
```

The tooling tests were written before `tools/notary/` existed; their first run failed at import
(`ModuleNotFoundError: No module named 'tools.notary.chain'`), which is the right reason for a module that
had not been written.

### Mutation check of the Solidity suite (T008)

The repository's mutation sweep does not reach Solidity, so each guard was broken in turn
(`forge test` after each; the source restored byte for byte afterwards). Every mutation compiled, and the
tests that went red are the ones that name the guard:

| Mutation | Tests that went red |
|---|---|
| owner check removed from commit | test_non_owner_cannot_commit |
| owner check removed from resolve | test_non_owner_cannot_resolve |
| zero-hash check removed | test_commit_zero_hash_reverts |
| duplicate-commit check removed | test_commit_twice_reverts_and_keeps_first |
| resolve of uncommitted allowed | test_resolve_uncommitted_reverts |
| double resolve allowed | test_resolve_twice_reverts_and_keeps_first |
| outcome range check removed | test_resolve_outcome_out_of_range_reverts |
| outcome range widened to 0..4 | test_resolve_outcome_out_of_range_reverts |
| zero owner accepted | test_constructor_rejects_zero_owner |
| owner ignores the constructor argument | test_owner_is_the_constructor_argument |
| block time stored as the bar time | test_block_time_is_not_bar_time, test_commit_emits_and_records, test_commit_twice_reverts_and_keeps_first |
| bar time stored as the block time | test_block_time_is_not_bar_time, test_commit_emits_and_records, test_commit_twice_reverts_and_keeps_first |
| Committed event not emitted | test_commit_emits_and_records |
| Resolved event not emitted | test_resolve_emits_and_records |
| Resolved event carries the wrong outcome | test_resolve_emits_and_records |
| contract accepts plain transfers | test_value_is_rejected |
| commit becomes payable | test_value_is_rejected |

No mutation left the suite green, so no missing test was found. "Owner ignores the constructor argument" is
caught only by `test_owner_is_the_constructor_argument` -- the other tests construct the notary from the test
contract itself, so `msg.sender` equals the intended owner; that test is why the thirteenth test exists.

### Rehearsal on a local chain (before touching the testnet)

Deploy, verify and smoke were run end to end against a throw-away `anvil` (chain id 31337, record in a
temporary file, nothing in the repository): the real `forge create --json` and `cast receipt --json` outputs
parse, signing through the keystore account works with no key on any command line, the on-chain code hashes to
the local compile (`0x3bd2e40e…390b`), `verify` passes before and after the smoke run. The in-memory fakes in
the unit tests could not have shown any of that.

## What was decided

- **A fake `ChainPort`, not a fake `cast` on `PATH`** (tasks T010 said the latter). The tools talk to a
  `Protocol`; the real `Chain` implements it over `cast`/`forge`, tests implement it in memory and can break
  one thing at a time. The real `Chain` is covered by the argv tests (T009) and by the anvil rehearsal.
- **Key mechanism (T002):** Foundry 1.7.1 signs with `--account <name> --password-file <file>`. Importing a
  key is the one awkward step (`cast wallet import` takes the key as an argument or from a terminal prompt);
  it was done once through a pty so the key never appeared in an argument list. The resulting keystore address
  equals the funded account. See `research.md` R5.
- **SC-005 is checked as "no 64-hex value on a line that names a key"**, over every tracked file
  (`test_no_tracked_file_holds_something_shaped_like_a_private_key`), not as "no 64-hex value anywhere":
  hashes and transaction ids are legitimately 64 hex digits. The plain-text `/root/.monad/deployer.env`
  (outside the repository) still holds the key; the tools never read it.
- **Missing Foundry fails** (T006), per the plan. CI installs it, pinned to 1.7.1.

## Deployment

Deployed to **Monad testnet (chain id 10143)** on 2026-10-08 from commit `4dd2b4969d4e` (the
`tested` commit, `contracts/` clean), after a dry run that showed the chain id, the deployer, 5 MON and a clean
tree.

| | |
|---|---|
| Contract | [`0x4a0963b8B35311411Bf17497F0CAeD20d5596682`](https://testnet.monadvision.com/address/0x4a0963b8B35311411Bf17497F0CAeD20d5596682) |
| Deployment transaction | [`0xf107deec3b28247b1cf5a25796979c7b39de9949d4823df6ec00c4f2b389fee2`](https://testnet.monadvision.com/tx/0xf107deec3b28247b1cf5a25796979c7b39de9949d4823df6ec00c4f2b389fee2) |
| Block / block time | 69218030 / 1791451264 |
| Owner = deployer | `0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131` |
| Runtime code hash | `0x3bd2e40e8561dde079903ba931d918903da7ffb2c83a5209cd8bb961aea4390b` (equals a fresh local compile) |
| Smoke `commit` | [`0x32a6bc0531e220cd8c2dd4120300f493f9409db3205e7088109dda5bcba09785`](https://testnet.monadvision.com/tx/0x32a6bc0531e220cd8c2dd4120300f493f9409db3205e7088109dda5bcba09785) |
| Smoke `resolve` (outcome 1) | [`0x15cfaaf120b86fe0cc87e27ec0f37b720374b18d490612f1deb904d9f4e8f84d`](https://testnet.monadvision.com/tx/0x15cfaaf120b86fe0cc87e27ec0f37b720374b18d490612f1deb904d9f4e8f84d) |
| Smoke hash | `0x777c574d57e87574ea9bd4cc477105b3546ba780a97db2eeb1bd5f4b3b955f7b` (a smoke hash, not a signal) |

**Read back, not assumed.** `deploy --broadcast` read the receipt (status 1, created address equal), hashed the
code at the address against the local compile, and read `owner()` before it wrote
`deployments/monad-testnet.json`. Then, independently of that tool: the same receipt, `owner()` and code hash
through a *different* public RPC (`rpc-testnet.monadinfra.com`, the first used `testnet-rpc.monad.xyz`), all
equal; `make notary-verify` exits 0 before and after the smoke run; `commitOf` and `outcomeOf` on the live
contract return what the smoke run sent.

**The reverts hold on the deployed contract, not only in the local suite** (simulated with `eth_call`, no
transactions): a second `commit` of the committed hash reverts with `0xbfec5558` (`AlreadyCommitted`), a
`commit` from another address with `0x30cd7471` (`NotOwner`), a second `resolve` with `0x6d5703c2`
(`AlreadyResolved`); each selector is the one `cast sig` gives for that error.

**Cost.** The deployment took the balance from 5.000000 to 4.939368 MON (about 0.061 MON); the smoke commit and
resolve about 0.015 MON together.

**One thing that looks wrong and is not.** The anvil rehearsal produced the same contract address. A contract's
address is a function of the deployer and its nonce, and both runs were this account's first transaction; the
rehearsal wrote to a temporary file and nothing from it reached the repository.

## What is still open

- The owner key still also exists in plain text in `/root/.monad/deployer.env` (outside the repository, mode 600, never read by the tools). It can be deleted now that the keystore is the only path; that is a decision for the key's owner, not done here.
- The deployer and the owner are the same account, so the contract's authority is one key held on this host. Accepted in the spec for a testnet MVP; a leak means a new contract.
- CI cannot be shown green until the unrelated MinIO image-pull failure is fixed (see the plan outcome); the
  Foundry step exists in the workflow but has not run on a runner.
- The "committed within N seconds of bar close" claim is [[REQ-INFRA-007]]'s to measure; nothing here asserts it.
