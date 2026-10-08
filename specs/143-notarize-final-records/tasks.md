---
description: "Tasks for REQ-INFRA-007 — notarize every final channel snapshot and decision"
---

# Tasks: Notarize every final channel snapshot and decision

**Input**: Design documents from `/specs/143-notarize-final-records/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/notary-bundle.md, quickstart.md

**Tests**: Written first. Each implementation task is preceded by the test task that must be shown failing for the
right reason (RED output goes into the implementation outcome note). A red suite cannot be committed (the
pre-commit hook runs it), so `tested` is recorded in the same commit as the code and the RED output is the
evidence. The pure core is also covered by mutation specs in `tests/mutations/` (the repository's acceptance
audit, `make mutate`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: US1 snapshot committed · US2 decision (incl. NO ALERT) committed · US3 outage-safe outbox ·
  US4 anyone can check · US5 the measured claim

## Path Conventions

`src/channelflow/notary/` · `tests/notary/` · `tests/mutations/` · `docs/notary.md` · `deployments/`

---

## Phase 1: Setup and measurements that decide a margin

- [X] T001 Record **before**: the full-suite test count; the duration of three consecutive worker passes (from `docker logs channelflow-worker-1`); the balance of `0x2A3b…2131`; the bars table snapshot count. These are the baselines for "the pass is not slower" and for the cost figures. **Done 2026-10-08**: 3,525 tests; channel part of a pass 1,012–1,290 s, flow step 10–14 min, cycle 28–35 min (research R12); balance 4.924015 MON; bars snapshots 14,020; channel_snapshots snapshots 6,891
- [X] T002 Settle R4 on the chain: send one `commit` of a throw-away hash with a gas limit about 40 % above the estimate (`cast send --gas-limit …`), compare the balance difference with `gasUsed × price` and with `gasLimit × price`; write the finding at the end of `research.md` R4. The result fixes whether the service's gas margin is a cost (FR-016 setting `…_GAS_MARGIN`). **Done 2026-10-08**: Monad charges the gas limit (research R4 finding); default margin 1.05
- [X] T003 [P] Add `eth-account` to `pyproject.toml` with the usual comment explaining why it and not `web3.py`; `uv lock`; confirm `uv sync --frozen --extra dev --extra tooling` and an image build still succeed; check the resolved set adds nothing that already has a different pinned major in `uv.lock`
- [X] T004 [P] Inventory the pass configuration: list the declared fields of `RollingOLSChannel`, `SignalMachine`, the detector it holds, and the settings that influence a pass (`CHANNELFLOW_GAP_THRESHOLD`, the timeframe); write the list in `research.md` R8 as it is today and note any value `config_hash` cannot encode

**Checkpoint**: baselines recorded; the gas-limit question answered; the dependency resolves.

---

## Phase 2: The pure core (scheme, records, context) — US1, US2, FR-001…FR-005, FR-017

### Tests first (confirm RED for the right reason)

- [X] T005 [P] [US1] `tests/notary/test_scheme.py`: the envelope is `"CFN" ‖ version ‖ frame(kind) ‖ frame(record) ‖ frame(config) ‖ frame(dataset) ‖ frame(commit)` (a hand-computed vector); **changing each of the four inputs, one at a time, changes the hash — for a snapshot and again for a decision (eight tests, SC-001)**; changing the kind or the scheme version changes it; the hash is independent of process and of call order; two different splits of the same bytes across frames hash differently (the `("ab","c")` vs `("a","bc")` case); a record of zero bytes and an absent one differ
- [X] T006 [P] [US1] `tests/notary/test_tree.py`: the RFC 9162 tree for sizes 1–9 against an independent, naive recursive implementation written in the test straight from the RFC text; inclusion proofs verify for every leaf of every size; a proof fails for a flipped leaf, a flipped path element, a wrong index and a wrong size; leaf and node prefixes make a leaf indistinguishable from an interior node impossible (second-preimage test: a node's bytes presented as a leaf do not verify); order independence is **not** claimed (the tree is a function of the ordered list)
- [X] T007 [P] [US1] [US2] `tests/notary/test_records.py`: a snapshot's canonical bytes equal `channels.SCHEMA.encode_row(channels.to_row(…))` exactly; a snapshot with `source_max_event_time_ns > as_of_ns` or a non-final bar is refused; decision rows: a candidate that reaches `expired` without `alerted` yields verdict `NO_ALERT` carrying the transition's reason; one that reaches `alerted` yields `ALERT`; every other step `STEP`; a candidate that was alerted and then `invalidated` is `STEP`, not `NO_ALERT`; `ordinal` follows the candidate's history; a suppression (`AuditRecord(status="suppressed")`) yields a `suppression` record with its recorded reason
- [X] T008 [P] [US1] `tests/notary/test_context.py`: absent, malformed (not 40 hex) or dirty commit → unnotarizable with the stated reason; an unhashable config value → unnotarizable, never skipped; `config_hash` changes when any **configuration** field of the channel, the machine or its detector changes, and does **not** change with the machine's state (`candidate`, `_awaiting_zone_exit`) — one parametrised test over the T004 inventory; **a completeness test enumerates every field of `RollingOLSChannel`, `SignalMachine` and `CloseBackInside` and fails unless each is classified as configuration or as state/observer**, so a parameter added without being classified fails the suite instead of staying out of the hash; the dataset reference is `dataset_reference({"bars": (id, content_hash)})`

### Implementation

- [X] T009 [US1] `src/channelflow/notary/scheme.py` (`# @trace: REQ-INFRA-007`): the envelope hash and the RFC 9162 tree, inclusion-proof generation and verification; pure, no I/O; reuse the lakehouse's length-prefix framing (export it if private)
- [X] T010 [US1] [US2] `src/channelflow/notary/records.py`: snapshot → canonical bytes and identity; `DECISION_SCHEMA` and the derivation of decision rows from a candidate's transitions; the suppression record; refusal of non-final / leaking snapshots
- [X] T011 [US1] `src/channelflow/notary/context.py`: `NotaryContext` from the pinned bars snapshot, `config_hash` over an **explicit list of configuration fields per component** (never a recursive walk: the machine holds state), and `CodeVersion` from the environment; "present or explicitly absent" per ADR-037
- [X] T012 [P] `tests/mutations/notary_scheme.toml` and `notary_records.toml`: mutate the framing (drop a frame, swap two inputs), the prefixes, the split rule, the odd-node rule, the verdict derivation, the finality refusal; every mutant caught or a survivor with a written reason; run `python -m tools.mutate` on them

**Checkpoint**: the hash and tree match the independent implementation; mutants caught.

---

## Phase 3: Registration in the pass — US1, US2, FR-004…FR-006, FR-010, FR-017

### Tests first

- [X] T013 [US1] `tests/notary/test_tables.py`: the four tables append-only; derived outbox state from the latest event; `unbatched`, `in flight`, `confirmed`, `unnotarizable` queries; a record is in at most one batch
- [X] T014 [US1] [US2] `tests/notary/test_registrar.py` (real `record_replay` over a fixture bar series, in-memory lakehouse): a pass registers each snapshot at or after the epoch exactly once; **a second pass over the same data registers nothing**; **a crash between the lakehouse write and the registration loses nothing** (the next pass registers it); a snapshot before the epoch is not registered; recomputing a registered snapshot's hash from the stored row + context equals the stored hash; `DecisionTracker` registers each *new* transition once, including a terminal transition of a candidate the signals table already holds in an earlier state (the defect of plan decision 1), and nothing on replays of old ones; the epoch setting excludes earlier bar closes; notarizer failure (a table error) does not stop the pass or change what the pass writes
- [X] T015 [US1] `tests/notary/test_pass_parity.py`: the lakehouse content of `channel_snapshots`, `signals`, `signal_transitions` and extrema after a pass is identical with the notary enabled and disabled; the pass reads **one** bars snapshot id throughout, and it equals every registered record's `dataset_snapshot_id`

### Implementation

- [X] T016 [US1] `tables.py`, `registrar.py` (`# @trace: REQ-INFRA-007`)
- [X] T017 [US1] [US2] Wire the pass **without touching `replay.py`**: `run_series` builds an `EventBus` per series, subscribes the registrar (`ChannelFitted`) and the `DecisionTracker` (`CandidateUpdated`) and passes it to `record_replay(bus=…)`; the runner comes from one `make_runner()` used both for the pass and for the config hash; `run_pass` pins `bars_table.current()` once and passes the snapshot id to every `read_bars`; the tracker's registered-identity set is loaded once per pass, not per series; the context (config hash from the runner actually used, the pinned dataset reference, the commit) is built once per pass
- [X] T018 Measure the pass again against T001 (three consecutive passes, notary on): record both in the outcome note; the operation counts are asserted in `test_notary_pass.py` (one extra read, at most one commit per series-timeframe); the fixture time ratio is **recorded, not asserted** (0.38 s → 0.45 s, 1.17×, +66 ms per series-timeframe ≈ 0.2 % of a live pass); the live bound is **1,419 s** (110 % of the longest of the five prior passes)

**Checkpoint**: a pass registers records, once, without changing what it writes.

---

## Phase 4: Batching, submission, the outbox — US3, FR-006…FR-009, FR-012, FR-016

### Tests first

- [X] T019 [US3] `tests/notary/test_batcher.py`: a window that has not elapsed forms nothing; an empty window forms nothing; a formed batch has deterministic leaf order `(bar_close, kind, record_id)` and a root equal to the tree over that order; `barTs` is the largest leaf bar-close in whole seconds and a non-whole-second bar close is an error (FR-011); a batch is immutable (re-running the batcher does not re-form it); the cap splits a backlog into several batches in order; unnotarizable records never enter a batch
- [X] T020 [US3] `tests/notary/test_submitter.py` with a fake chain: chain unreachable → nothing lost, `failed` events accumulate, the next tick retries the **same** root; chain returns → each batch sent exactly once and in order; **crash between send and recording** (fake raises after the send) → on restart `commitOf(root)` reconciles and nothing is sent twice; a root the contract reports as already committed is confirmed from its `Committed` log, not retried; a receipt that never arrives stays pending; **confirmed requires the receipt and the `finalized` read-back**; balance below the floor → `held`, nothing sent, the reason in the event; gas price above the ceiling → `held`; an unexpected exception in one batch does not end the loop
- [X] T021 [US3] `tests/notary/test_outage_pass.py`: with the chain made unreachable, a pass over the fixture series produces and stores exactly the same signals and snapshots, with the same operation counts as the pass without the notary and the same lakehouse content (SC-003); the time is recorded, not asserted, and the outbox listing shows count, oldest age and last error

### Implementation

- [X] T022 [US3] `batcher.py` and `submitter.py` (`# @trace: REQ-INFRA-007`)
- [X] T023 [P] `tests/mutations/notary_batcher.toml` and `notary_submitter.toml` (window rule, order, cap, reconcile-before-send, confirmation condition, held conditions, duplicate-send guard); every mutant caught or a survivor with a reason

---

## Phase 5: The chain client and the signer — FR-015

### Tests first

- [X] T024 [P] `tests/notary/test_chain.py` with a fake HTTP transport: `commit(bytes32,uint64)` calldata is selector + two 32-byte words, equal to `cast calldata` for a fixed example (the expected bytes are written into the test); the signed raw transaction recovers to the signer's address and carries chain id 10143 and the right nonce; a gas price above the ceiling is refused before signing; `commitOf` decoding; a Foundry-format keystore (a throw-away one generated in the test) decrypts; **start-up refuses when the signing address is not `owner()`** and logs only the address; no log line or exception text contains the key or the password
- [X] T025 `src/channelflow/notary/chain.py`: the `NotaryChain` port and the JSON-RPC implementation (`httpx` + `eth-account`), nine calls, finalized-tag read-back, `Committed` log lookup for reconcile

**Checkpoint**: the whole outbox path runs against fakes; the real client is unit-tested against a fake transport.

---

## Phase 6: Verification, export, latency, the claim — US4, US5, FR-013, FR-014

### Tests first

- [X] T026 [US4] `tests/notary/test_verify.py`: a notarized record verifies as committed with block, transaction and latency; any altered field → "not committed"; a record in an unconfirmed batch → "pending", never "committed"; `export` then `verify bundle` succeeds **using only the bundle and the fake chain** (no lakehouse access); a bundle whose inclusion path is altered fails; the verifier states "no later than", never "before"
- [X] T027 [US5] `tests/notary/test_latency.py`: median / p95 / max of `block_time − bar_close_time` over fixture leaves, per leaf and not per batch; sample size, series and window reported; a window with fewer records than the success criterion is labelled insufficient rather than reported as a result
- [X] T028 [US5] `tests/notary/test_claim.py` (SC-007): no tracked user-facing file (`README.md`, `docs/`, the web app's strings) claims a commit precedes a price move; if `deployments/monad-testnet-latency.json` exists, `docs/notary.md` quotes its median, p95 and max exactly; if it does not exist, `docs/notary.md` says "not yet measured" and contains no figure

### Implementation

- [X] T029 [US4] [US5] `verify.py` (`verify`, `export`, `bundle`), `latency.py`; `docs/notary.md` (what is notarized, what a commit proves and does not, "not yet measured")

---

## Phase 7: Service, configuration, deployment wiring — FR-015, FR-016, SC-008

### Tests first

- [X] T030 [P] `tests/notary/test_main.py`: configuration is read and validated with each missing/malformed variable named; the loop continues after a tick that raises; the `outbox` command lists unbatched, unconfirmed and unnotarizable records with reasons; metrics for the six gauges in `data-model.md` are exposed in the existing exposition format
- [X] T031 [P] `tests/unit/deploy/test_notary_compose.py`: `docker-compose.yml` has a `notary` service; the worker and every other service mount **no** notary secret; no environment value in the compose file or `.env.example` carries a key; secrets are named by variable, not by a literal path; the `Dockerfile` takes `CHANNELFLOW_CODE_COMMIT` and `CHANNELFLOW_CODE_DIRTY` as build arguments and no key-shaped value appears anywhere tracked (extends the REQ-WP-072 guard)

### Implementation

- [X] T032 `main.py` (loop, `outbox`, metrics) and the settings in `src/channelflow/settings.py`
- [X] T033 [P] `.env.example` (documented `CHANNELFLOW_NOTARY_*`), `docs/deployment.md` (a section; every variable named in backticks, which a repository test requires), `Makefile` (`notary-build-info`), `Dockerfile` (build args → env), `docker-compose.yml` (`notary` service, secrets, worker environment)
- [ ] T034 Gate: `make lint`, `make typecheck` (the new package is under `mypy --strict`), `make test-fast`; `make graph` once; `status: tested`; commit with explicit paths (pre-commit ≈ 7 minutes; do not edit the tree while it runs). **No live deployment in this commit**

**Checkpoint**: everything that needs no running stack is green and committed from a clean tree.

---

## Phase 8: Live (outward-facing, in order)

- [ ] T035 Prepare the secrets directory outside the repository: copies of the keystore and password file owned by uid 10001, mode 400; record the paths in the local `.env` only (never in a tracked file); check by reading them as that uid
- [ ] T036 Build from the clean committed tree with the commit baked in (`make notary-build-info`), then `docker compose up -d --no-deps --build worker notary` — **only** those two services. Check: the worker's start time changed and no other container's did; the `notary` log shows the signing **address** equal to `owner()` and nothing else secret; the first worker pass after restart completes within the live bound of T018 (1,419 s)
- [ ] T037 Let it run until at least one batch is `confirmed` on testnet; open the transaction on the explorer; run `verify` on a snapshot and on a decision from that batch; `export` one and `verify bundle` it with only the public RPC
- [ ] T038 Measurement (SC-006): leave the stack running for at least one hour and until at least 50 records from at least 3 series are confirmed; run `latency`; write `deployments/monad-testnet-latency.json`; update `docs/notary.md` to quote it exactly
- [ ] T039 Outage drill on the live stack (SC-003, SC-004): block the notary's RPC for one window (stop the `notary` container; do **not** touch the worker); confirm worker passes continue and the outbox grows and is visible; restart the notary; confirm the backlog drains once each and that `commitOf` shows no duplicate; record the evidence
- [ ] T040 Balance and runway: record the balance now and the cost per day actually observed; compare with the plan's 0.39 MON / day; state the remaining runway

---

## Phase 9: Close-out

- [ ] T041 Record **after** and the implementation outcome note: RED output (T005…T008, T013…), the mutation tables, the T002 gas finding, pass times before/after, the live evidence (T037…T040) with explorer links, the measured latency, the `signal_transitions` defect as a candidate requirement, and what was not done (the suppression kind has no live producer; alert links are 008)
- [ ] T042 `make graph` once, then `.venv/bin/python -m tools.trace.cli validate`; set `status: implemented`; commit with explicit paths

---

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 four-input hash | T005, T009, T011 |
| FR-001a kind + scheme version | T005, T009, T012 |
| FR-002 repository's own encoding | T007, T010, T011 |
| FR-003 changes with each input, independent of process | T005, T008 |
| FR-004 snapshots; non-final / leaking refused | T007, T010, T014 |
| FR-005 decisions incl. NO ALERT and suppression | T007, T010, T014 |
| FR-006 at most once | T014, T017, T019, T020 |
| FR-007 async, never blocks | T021, T018, T036 |
| FR-008 durable visible outbox | T013, T020, T021, T030, T039 |
| FR-009 done = receipt + read-back; reconcile | T020, T025, T037 |
| FR-010 absent commit/config/dataset or dirty → unnotarizable | T008, T011, T014, T030 |
| FR-011 explicit time, whole seconds | T019, T025, T027 |
| FR-012 sizing before design | plan.md "Volume sizing", T040 |
| FR-013 verification command | T026, T029, T037 |
| FR-014 measured latency; no "before the move" | T027, T028, T038 |
| FR-015 signing authority from mounted keystore | T024, T031, T035, T036 |
| FR-016 configuration | T030, T032, T033 |
| FR-017 one hashing path live and replay | T014, T015, T026 |
| FR-018 traceability | every source file carries `# @trace:`; every test the marker |
| SC-001 eight hash tests | T005 (four inputs) + T014 (stored snapshot) + T014/T007 (stored decision) |
| SC-002 one path for NO ALERT and alert | T007, T014 |
| SC-003 outage bound | T021, T018, T039 |
| SC-004 drain once; no wedge | T020, T039 |
| SC-005 sizing with numbers | plan.md, T040 |
| SC-006 ≥ 50 records, ≥ 3 series, ≥ 1 h | T038 |
| SC-007 claim test | T028 |
| SC-008 key nowhere; mounted keystore | T031, T035, T036, T042 (diff scan) |

## Dependencies

T001, T002 first (baselines, the gas answer). T003, T004 before Phase 2. Phase 2 tests (T005–T008) precede T009–T011;
T012 after them. Phase 3 needs Phase 2. Phase 4 needs T013 and the pure core. Phase 5 is independent of Phase 3 and
can run alongside Phase 4. Phase 6 needs Phases 2–5. Phase 7 needs Phase 6. **Phase 8 needs T034 committed** (clean
tree for the baked commit). T038 needs T037; T039 needs T038's stack running; T042 last.
