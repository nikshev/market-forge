---
traces: [REQ-INFRA-006]
status: draft
---

# Feature Specification: SignalNotary contract on Monad testnet

**Feature Branch**: `142-signal-notary-contract`

**Created**: 2026-10-08

**Status**: Draft

**Input**: [[REQ-INFRA-006]] — user-directed integration 2026-10-03; touches PRD §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity). Principles I, II, III, X, XI, XIV.

## Context

The product's central promise is that signals are not repainted. While the signal journal sits in a private
database that promise is only words. A hash of each decision written to a public chain makes it checkable by
anyone — provided what is hashed is exactly what was shown.

This feature is the **contract and its deployment only**. *What* is hashed and *when* is
[[REQ-INFRA-007]]; the alert link is [[REQ-INFRA-008]]; outcomes are written by [[REQ-INFRA-009]]. Nothing
here decides a record's encoding: the contract treats a hash as 32 opaque bytes.

### What a block timestamp does and does not prove

A commit proves the hash existed **no later than that block**. It does not prove a signal preceded a price
move; that holds only if the commit lands before the move. The claim the product may make is "committed
within N seconds of bar close" with N measured ([[REQ-INFRA-007]]), never "before the move". This spec
therefore makes the contract store the **bar's close time as supplied by the committer** (`barTs`,
`bar_close_time` in the sense of Principle II) separately from the **block time** the chain assigns
(`block_time`). The two are never the same field and the contract never derives one from the other.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Commit a hash, once (Priority: P1)

The system's operator account records that a hash was committed, together with the bar's close time.

**Why this priority**: Without commit nothing else in the Monad work exists.

**Independent Test**: Local contract tests (no network) — commit emits `Committed(hash, barTs, committer)`;
the stored record is readable; a second commit of the same hash reverts.

**Acceptance Scenarios**:

1. **Given** a deployed contract and its owner, **When** the owner commits `h` with `barTs`, **Then** a
   `Committed(h, barTs, owner)` event is emitted and the commit is readable by `h`.
2. **Given** `h` already committed, **When** the owner commits `h` again (any `barTs`), **Then** the call
   reverts and the first record is unchanged.
3. **Given** the zero hash, **When** the owner commits it, **Then** the call reverts (an unset slot must not
   be confusable with a committed one).

---

### User Story 2 - Resolve a committed hash, once (Priority: P1)

The owner records the outcome of a previously committed hash: `1` target hit, `2` invalidated, `3` expired.

**Why this priority**: The public history of outcomes ([[REQ-INFRA-009]]) rests on this call.

**Independent Test**: Local contract tests — resolve emits `Resolved(hash, outcome)`; resolving an
uncommitted hash, resolving twice, and an outcome outside `1..3` each revert.

**Acceptance Scenarios**:

1. **Given** `h` committed, **When** the owner resolves it with `outcome` in `1..3`, **Then** `Resolved(h,
   outcome)` is emitted and the outcome is readable.
2. **Given** `h` never committed, **When** resolved, **Then** the call reverts.
3. **Given** `h` already resolved, **When** resolved again (same or different outcome), **Then** the call
   reverts and the first outcome is unchanged.
4. **Given** `h` committed, **When** resolved with `0` or `4` or any value outside `1..3`, **Then** the call
   reverts and `h` stays resolvable.

---

### User Story 3 - Only this system writes (Priority: P1)

The contract is a notary of this system's own decisions, not a public registry.

**Independent Test**: A non-owner calling `commit` or `resolve` reverts; the failed call changes nothing.

**Acceptance Scenarios**:

1. **Given** an account that is not the owner, **When** it calls `commit` or `resolve`, **Then** the call
   reverts and no record or event results.
2. **Given** a deployment, **When** the constructor receives the zero address as owner, **Then**
   deployment reverts.

---

### User Story 4 - A real deployment anyone can check (Priority: P1)

The contract is deployed on **Monad testnet** and the repository records its address and deployment
transaction, which is the evidence for the hackathon submission's *Live product* field.

**Independent Test**: A script reads the recorded transaction back from the chain and compares the
recorded address, the deployed code and the owner with the repository's contract.

**Acceptance Scenarios**:

1. **Given** the recorded deployment transaction hash, **When** it is read from the testnet RPC, **Then** its
   receipt succeeded, created the recorded address, and the code at that address matches the compiled
   contract.
2. **Given** the repository before the deploy has succeeded, **When** it is searched, **Then** no address or
   transaction hash for the contract appears anywhere (nothing claims a deployment that did not happen).
3. **Given** the deploy account's key, **When** the repository is searched (tracked files and history),
   **Then** it appears nowhere; only its public address is recorded.

### Edge Cases

- `barTs` of `0`, or far in the future: the contract does not judge it (it is the committer's claim, and
  validating it would need a clock the contract does not trust); [[REQ-INFRA-007]] owns its correctness.
- Two commits in one block, or the same hash from two writers: the second reverts; there is one writer.
- Owner key lost or leaked: no transfer or rotation exists in this MVP. A leaked key allows forged
  commits under this address, so a new contract and address would be deployed and the old one declared
  retired in the outcome note. Accepted for a testnet MVP; recorded, not hidden.
- A resolve whose outcome is later believed wrong: it cannot be changed (Principle III); a correction is
  a new record elsewhere, never an edit.
- Chain reorganisation or an RPC returning a stale view: the deployment check reads the receipt and the
  code, and treats a missing receipt as "not deployed", never as success.
- Testnet reset or deprecation: the recorded address then no longer resolves; this is stated in the
  outcome note, and the contract can be redeployed from the same source.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The contract MUST expose `commit(bytes32 hash, uint64 barTs)` that records the hash with the
  supplied bar close time and the block time, and emits `Committed(hash, barTs, committer)`.
- **FR-002**: `commit` MUST revert for a hash already committed and for the zero hash.
- **FR-003**: The contract MUST expose `resolve(bytes32 hash, uint8 outcome)` that records the outcome of a
  committed hash and emits `Resolved(hash, outcome)`; outcomes are `1` target hit, `2` invalidated, `3`
  expired.
- **FR-004**: `resolve` MUST revert for an uncommitted hash, for an already resolved hash, and for an
  `outcome` outside `1..3`.
- **FR-005**: A committed record and a resolved outcome MUST be unchangeable by any later call; the contract
  MUST NOT have any function that deletes or overwrites either.
- **FR-006**: Only the owner configured at deployment MAY call `commit` and `resolve`; any other caller
  MUST revert. The owner MUST be a constructor argument (configuration, Principle X), not the compiler's
  default, and MUST NOT be the zero address.
- **FR-007**: The contract MUST keep the bar close time (`barTs`) and the block time as two separate stored
  values (Principle II) and MUST expose read access to a hash's commit (`barTs`, block time, committer),
  its outcome, and the owner.
- **FR-008**: The contract MUST hold no funds and MUST reject value sent with a call or by plain transfer.
- **FR-009**: The repository MUST contain the contract source, its tests and a deploy script. The tests MUST
  run with no network access.
- **FR-010**: The deploy script MUST take the RPC URL, chain id and signing key from the environment and
  MUST refuse to run against a chain id other than the configured one. The signing key MUST NOT be
  logged, committed or placed in any tracked file.
- **FR-011**: The contract MUST be deployed to Monad testnet (chain id 10143). Its address and deployment
  transaction MUST be recorded in the outcome note and `.env.example` (as documented variables with their
  meaning) **only after** the transaction and the code at the address have been read back from the chain.
- **FR-012**: A verification script MUST re-read the recorded deployment from the chain and fail
  loudly when the receipt is missing or failed, the created address differs, the deployed bytecode
  differs from the compiled source, or the owner differs from the configured account.
- **FR-013**: A smoke run on testnet MUST commit one real hash and resolve it, and the two transaction
  hashes MUST be recorded; this proves the deployed contract, not just the compiled one.
- **FR-014**: Every file added carries a requirement trace in the form the trace tooling reads
  (Principle XIV). Where the file type is not read by the tooling, the Python deploy and verification
  wrappers carry `# @trace: REQ-INFRA-006` and the contract test suite is driven from a pytest test
  carrying `@pytest.mark.trace("REQ-INFRA-006")`.

### Key Entities

- **Commit record**: hash (32 bytes, key), bar close time (committer-supplied, seconds), block time (chain
  assigned, seconds), committer. Immutable once written.
- **Outcome record**: hash (key), outcome code `1..3`. Immutable once written; exists only for a committed
  hash.
- **Owner**: the one account allowed to write. Fixed at deployment.
- **Deployment record**: chain id, contract address, deployment transaction hash, deploy block, owner
  address, source commit; written to the outcome note only after read-back.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every behaviour in FR-001…FR-008 has at least one test that fails on a contract lacking
  it, and the whole contract suite passes with the network disabled.
- **SC-002**: The six reverts the requirement names (duplicate commit, uncommitted resolve, double
  resolve, non-owner write, out-of-range outcome — plus zero hash) each have their own test.
- **SC-003**: A reviewer, from the repository alone, can run one command that reads the recorded
  deployment from the public testnet RPC and gets a pass/fail with the reason.
- **SC-004**: The deployed address on testnet shows one successful commit and one successful resolve of a
  smoke hash, each linked from the outcome note to the explorer.
- **SC-005**: A search of the working tree and of git history finds the deploy private key zero times.

## Assumptions

- Monad testnet (chain id 10143) is reachable through a public RPC; the endpoint is configuration and
  the default is taken from the network's published list.
- The deploy account is a throw-away testnet account whose key lives outside the repository; it was funded
  from a public faucet on 2026-10-08 (balance read back from the chain before deploying).
- A single owner is sufficient for the MVP; multi-writer, ownership transfer and upgradeability are out
  of scope and recorded as deliberate omissions.
- The contract does not validate that a hash corresponds to any record; that binding is
  [[REQ-INFRA-007]]'s encoding and its reproducibility test.
- Gas cost is irrelevant to correctness here; volume against testnet fees is sized in
  [[REQ-INFRA-007]]'s plan.
- Solidity tooling (Foundry) is available on the development host; whether the CI gate installs it, and
  how the contract suite joins the fast gate, is decided in the plan.
