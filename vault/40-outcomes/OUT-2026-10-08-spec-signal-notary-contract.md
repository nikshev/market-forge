---
id: OUT-2026-10-08-spec-signal-notary-contract
step: spec
records: [REQ-INFRA-006]
commit: null
---

## What was done

Specified [[REQ-INFRA-006]] as `specs/142-signal-notary-contract/spec.md`: four user stories (commit once,
resolve once, owner-only writes, a deployment anyone can re-check), fourteen functional requirements, five
success criteria. The deploy account was created on 2026-10-08 with its key kept outside the repository
(`/root/.monad/deployer.env`, mode 600) and funded from the public faucet; 5 MON was read back from the
chain (chain id 10143) before any work began.

## What was decided

- The contract stores the committer-supplied `barTs` and the chain's block time as **two fields**, never
  derived from one another (Principle II). This is what keeps the product's claim honest: "committed within
  N seconds of bar close", with N measured in [[REQ-INFRA-007]].
- The zero hash is rejected: an unset slot must not be confusable with a committed one.
- The owner is a constructor argument that cannot be the zero address. No transfer, no rotation, no
  upgrade: a leaked key means a new contract and a retired old one, written down rather than engineered
  away for a testnet MVP.
- The contract holds no funds and rejects value.
- `barTs` is not validated by the contract (no trusted clock on-chain); its correctness belongs to
  [[REQ-INFRA-007]].
- Beyond the requirement's six named reverts, the spec adds a **read-back verification** (FR-012) and a
  **smoke commit + resolve** on testnet (FR-013). Without them "deployed" would mean "a transaction was
  sent", not "this contract is what runs at that address".

## What is still open

- **Trace tooling does not read `.sol`.** `CODE_SUFFIXES` in `tools/trace/collect.py` is
  `.py .ts .tsx .js .jsx .yml .yaml`, so rule R8 needs the `# @trace: REQ-INFRA-006` marker in a Python file
  (deploy / verify wrappers), and rule R2 needs a pytest test that runs the Solidity suite. The plan must
  choose the shape; widening `CODE_SUFFIXES` to `.sol` is a tooling change and out of scope here.
- **Foundry in the gates.** `forge` exists on this host, not in `.github/workflows/ci.yml`. A pytest that
  silently skips when `forge` is missing would not earn `VERIFIES` ([[REQ-INFRA-006]] must not reach
  `implemented` on a skip), so the plan must either install it in CI or choose a different runner. The
  CLAUDE.md rule applies: no check may be absent from both gates.
- **Deploy is outward-facing.** It spends testnet funds and publishes an address; the plan keeps it a
  separate, explicitly triggered step after the tests are green.
- The deployed address and transactions are **not** recorded here: none exists yet.
