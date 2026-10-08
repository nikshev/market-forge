---
id: OUT-2026-10-08-plan-signal-notary-contract
step: plan
records: [REQ-INFRA-006]
commit: null
---

## What was done

Planned [[REQ-INFRA-006]] in `specs/142-signal-notary-contract/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/signal-notary-abi.md`, `quickstart.md`. Two things were measured rather than assumed, on this
host, today: a scratch Foundry project compiled with a pinned `solc 0.8.28` (fetched on first use) and
`forge test --json` returned a per-test status; and the Monad testnet RPC answers (`chain-id` 10143, client
`Monad/0.16.3`).

## What was decided

- **The `.sol` suite reaches the trace graph through a pytest driver**, not through widening
  `CODE_SUFFIXES`. The driver holds an explicit list of expected forge test names and has one traced case per
  name, plus a completeness check. Rejected: widening the suffix list (changes what the graph means for every
  requirement), and a single "forge exited 0" case (passes on an empty suite).
- **Missing Foundry fails; it does not skip.** A skip earns no `VERIFIES` and would let the fast gate pass on
  a host that never ran the contract tests.
- **`cast`/`forge` from Python, no web3.py.** The runtime chain client is [[REQ-INFRA-007]]'s decision, made
  with its volume numbers.
- **Owner in storage, not `immutable`**, so "deployed code equals compiled code" stays an exact comparison.
- **No forge-std**; the three cheatcodes needed are vendored. Rejected: a git submodule every fresh checkout
  and CI run would have to fetch.
- **Dry-run is the default; `--broadcast` deploys**, and refuses a dirty `contracts/` tree so `source_commit`
  is the code that ran. The deployment record is written last, after receipt, address, code hash and `owner()`
  have all been read back; `.env.example` and the record must agree or both be absent.
- **The key never reaches argv**; a test asserts on the argv the tool builds.

## What is still open

- **CI is red for an unrelated reason** (MinIO image pull, `docker: unauthorized`, 2026-10-03), so "Foundry
  runs in the full gate" will be true of the workflow file but cannot be shown by a green run until that is
  fixed. Not fixed here; named so it is not mistaken for a result.
- **Which key mechanism Foundry 1.7.1 supports** (keystore with password file, or a signer environment
  variable) is confirmed in the first task, not assumed; the requirement on it (never in argv) is fixed.
- **Exact `evm_version`.** `cancun` is chosen as conservative; if Monad rejects the create for an opcode, the
  failure is immediate and the setting is the first thing to change.
- Mutation check of the Solidity suite (remove each guard, see its test go red) is a task, recorded in the
  implementation outcome, because the repository's mutation sweep does not reach Solidity.
