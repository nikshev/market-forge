# Implementation Plan: SignalNotary contract on Monad testnet

**Branch**: `142-signal-notary-contract` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/142-signal-notary-contract/spec.md`

## Summary

A ~60-line Solidity contract with `commit`, `resolve` and one owner, tested offline with Foundry, driven from
pytest so the repository's trace tooling can see the tests pass, plus a small Python tool (`tools/notary/`)
that deploys it, reads the deployment back from the chain, and records it only after that read-back. The
contract is deliberately boring; most of the plan is about the three things around it that are not: how a
`.sol` test earns a `VERIFIES` edge, how the deploy avoids ever claiming something that did not happen, and
how the key stays out of the repository.

## Technical Context

**Language/Version**: Solidity 0.8.28 (pinned in `foundry.toml`); Python 3.12 for the tooling.

**Primary Dependencies**: Foundry 1.7.1 (`forge`, `cast`) — already on this host; **no Solidity library**
(no forge-std, no OpenZeppelin): the cheatcode interface the tests need is a dozen lines vendored in
`contracts/test/utils/Vm.sol`, and an ownership library for one `require` would be more code than the check.
No new Python dependency: the tooling shells out to `cast`/`forge` (see research.md R3).

**Storage**: On-chain only: two mappings in the contract. The deployment record is a committed JSON file.

**Testing**: `forge test` for the contract (no network); pytest for the tooling and as the driver that makes
the forge results visible to `make markers`.

**Target Platform**: Monad testnet, chain id 10143. EVM version `cancun` (a subset of what Monad runs; the
contract uses nothing newer).

**Project Type**: A contract directory plus a CLI tool in the existing repository.

**Performance Goals**: None. Correctness only (Principle XII); gas is irrelevant at this scale.

**Constraints**: Tests must not need a network once `solc` is cached. The private key must not appear in a
process argument list, a log line, a tracked file or git history. The deploy is outward-facing and runs only
on an explicit flag.

**Scale/Scope**: One contract, one network, one owner.

## Constitution Check

*GATE: passed before research; re-checked after design — still passes.*

| Principle | Status |
|---|---|
| I. No look-ahead | Not engaged here. The contract hashes nothing; what is hashed and when is [[REQ-INFRA-007]]. |
| II. Time is not one thing | **Engaged and satisfied**: `barTs` (committer's `bar_close_time`) and the block time are two stored fields, never derived from one another (FR-007). |
| III. History is immutable | The contract has no function that overwrites or deletes (FR-005); tested for commit and for resolve. |
| IV, V | N/A (no model, no probability). |
| VI. Every feature documented | `contracts/signal-notary-abi.md` records semantics, units and the time meaning of each field. |
| VII. Live = replay | N/A here; the notary is called by one code path in [[REQ-INFRA-007]]. |
| VIII | N/A (not a connector). |
| IX. No automatic execution | The contract moves no funds and rejects value (FR-008). |
| X. Thresholds are configuration | RPC URL, chain id, owner, explorer URL are environment, not literals. The `1..3` outcome range is protocol, not a trading threshold. |
| XI. Reproducible | The deployment record carries the source commit and the keccak of the deployed bytecode, so the claim "this address runs this source" is re-checkable. |
| XII. Correctness precedes performance | Yes; nothing is optimised. |
| XIII. Incremental | The contract and its deployment only; encoding, alert links and outcomes stay in 007–009. |
| XIV. Traceable | Python wrappers carry `# @trace:`; the forge suite is driven by traced pytest cases (research.md R1). |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/142-signal-notary-contract/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── signal-notary-abi.md
└── tasks.md             # /sdd-tasks
```

### Source Code (repository root)

```text
contracts/
├── foundry.toml                  # solc 0.8.28, evm cancun, no remappings
├── src/SignalNotary.sol
└── test/
    ├── SignalNotary.t.sol        # the offline suite
    └── utils/Vm.sol              # the dozen cheatcode lines the suite needs

tools/notary/
├── __init__.py
├── chain.py                      # thin typed wrappers over `cast`; builds argv, never logs secrets
├── deploy.py                     # dry-run by default; --broadcast deploys; writes the record last
├── verify.py                     # re-reads the recorded deployment from the chain; exit 1 with the reason
└── smoke.py                      # one real commit and one real resolve on the deployed contract

deployments/
└── monad-testnet.json            # ABSENT until a deployment has been read back

tests/contracts/
└── test_signal_notary_suite.py   # runs `forge test --json` once; one traced case per forge test
tests/tools/notary/
├── test_chain.py                 # argv never carries the key; the wrong chain id is refused
├── test_deploy.py                # fake `cast`: record written last, never on a failed read-back
└── test_record.py                # the committed record and `.env.example` agree, or both are absent
```

Also touched: `Makefile` (`contracts-test`, `notary-verify`), `.github/workflows/ci.yml` (install Foundry),
`.gitignore` (`contracts/out`, `contracts/cache`), `.env.example` (documented `MONAD_*` variables),
`docs/deployment.md` (one section: the notary).

**Structure Decision**: `contracts/` at the top level beside `src/` and `apps/`; the Python tooling under
`tools/` with the other developer-facing programs, not under `src/channelflow/`, because it is run by a
human at deploy time and is not part of the running product. [[REQ-INFRA-007]] will need a *runtime* chain
client; that belongs in `src/channelflow/` and is planned there, not pre-built here.

## Design decisions, with what was rejected

1. **A pytest driver for the forge suite, not a widened `CODE_SUFFIXES`.** `tools/trace/collect.py` reads
   `.py .ts .tsx .js .jsx .yml .yaml`. Adding `.sol` would change what the trace graph means for every
   requirement, for the sake of one; the pytest driver changes nothing about the graph. The driver runs
   `forge test --json` once per session, holds an *explicit list* of the expected forge test names, and has
   one traced pytest case per name — so a deleted or renamed forge test fails a pytest case, and a forge
   test that is not in the list fails a completeness check. Rejected: one pytest case that asserts "forge
   exited 0" — it would pass with an empty suite.
2. **Foundry's absence is a failure, not a skip.** A skipped test earns no `VERIFIES` and, worse, would let
   the fast gate pass on a host that never ran the contract tests. The case fails with the install command.
   Rejected: `pytest.skip` when `forge` is missing.
3. **Shell out to `cast`/`forge`; no `web3.py`.** The deploy and the read-back are a handful of calls; a
   new dependency (with its transitive tree) for them is more surface than the task. [[REQ-INFRA-007]] will
   decide the runtime client with the volume numbers in hand. Rejected: web3.py now.
4. **Owner in storage, not `immutable`.** An immutable is baked into the deployed bytecode, which would make
   the "deployed code equals compiled code" comparison need masking. A storage owner keeps FR-012 an exact
   comparison. The extra SLOAD is irrelevant here.
5. **No forge-std.** Vendoring the three cheatcodes the suite uses (`prank`, `expectRevert`, `warp`) avoids a
   git submodule that CI and a fresh checkout would have to fetch. Rejected: `forge install`.
6. **The deploy is dry-run unless `--broadcast`.** Dry-run prints the chain id, the deployer, its balance and
   the exact transaction it would send. `--broadcast` additionally refuses a dirty `contracts/` tree so that
   `source_commit` is the code that ran.
7. **The record is written last.** `deployments/monad-testnet.json` is written only after the receipt
   succeeded, the created address matched, the on-chain code matched, and `owner()` matched. A test with a
   fake `cast` proves a failing read-back leaves no record. `.env.example` carries the same address under
   `MONAD_NOTARY_ADDRESS`; `test_record.py` fails if exactly one of the two exists or they disagree.
8. **The key never reaches argv.** `forge create`/`cast send` use an encrypted Foundry keystore account
   (`--account`, with a password file kept outside the repository), never `--private-key <hex>`. The first task
   confirms the flags on the installed Foundry; the test asserts on the argv the tool builds.

## Risks

- **CI is currently red for an unrelated reason** (`docker: unauthorized` pulling MinIO at the "Start the
  object store" step, 2026-10-03). Adding Foundry to the workflow cannot be shown green until that is fixed;
  until then "runs in the full gate" is true of the configuration, not yet of a green run. Recorded in the
  outcome note; fixing CI is its own item.
- **First compile needs the network** to fetch `solc 0.8.28` (cached afterwards under `~/.foundry`). In CI
  the runner has network; on an offline host the cache must be primed once.
- **Testnet may reset.** Then the recorded address stops resolving; `verify.py` says so rather than
  failing obscurely, and the contract is redeployed from the same source.
- **Owner key is a single point of forgery.** Accepted and written down in the spec; a new contract is the
  remedy, not a rotation feature.

## Complexity Tracking

None.
