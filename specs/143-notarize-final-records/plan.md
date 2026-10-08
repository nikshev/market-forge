# Implementation Plan: Notarize every final channel snapshot and decision

**Branch**: `143-notarize-final-records` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/143-notarize-final-records/spec.md`

## Summary

The channel pass already writes every final snapshot once. This feature adds, beside it, a record of *what was
written and in what context* (config hash, input dataset snapshot, code commit), groups those records into
batches, and commits one Merkle root per batch through the deployed `SignalNotary`. Registration happens inside
the worker with no chain access and no key; a separate small `notary` service owns the key, forms batches,
sends them, confirms them and drains the outbox. A verification command and an exportable bundle let anyone
check a record against the chain.

The shape follows from numbers measured on the running system on 2026-10-08, not from preference: see
"Volume sizing". One transaction per record is ruled out by arithmetic (about 6 hours of the budget); one root
per 30 minutes fits for about 13 days.

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: existing `httpx`, `eth-hash[pycryptodome]` (Keccak), `pyiceberg`, `pyarrow`; **one new**:
`eth-account` (decrypts a Foundry keystore and signs a transaction; no hand-rolled secp256k1 or RLP).
No `web3.py`: of its surface the service needs nine JSON-RPC calls.

**Storage**: four new append-only lakehouse tables (`notary_records`, `notary_batches`, `notary_leaves`,
`notary_events`) on the same Iceberg plane as the rest.

**Testing**: pytest with an in-memory chain; the real chain is exercised by a measurement run on testnet
(SC-006), not by the unit suite.

**Target Platform**: the existing compose stack; one new service (`notary`); changes to `worker`, `Dockerfile`.

**Performance Goals**: with the notary enabled a worker pass takes no more than **110 % of the baseline pass time**
recorded before the change (registration is local appends and one pinned read), including with the chain
unreachable (SC-003); chain traffic ≈ 48 transactions a day.

**Constraints**: the worker never holds a key; a chain outage delays notarization only; Principle I and III.

**Scale/Scope**: ≈ 2,450 records a day today (5 series × 5 timeframes + ≈ 140 decisions), linear in series.

## Volume sizing (FR-012, SC-005)

Measured in the worker container on 2026-10-08, read-only; per-transaction cost from the deployed contract.

| Input | Value | Source |
|---|---|---|
| Series | 5 (`binance` BTC/ETH/SOL, `bybit` BTC, `okx` BTC-SWAP) | `channel_snapshots` |
| Timeframes producing snapshots | 5 (5m, 15m, 30m, 1h, 4h; 1d and 1w are configured but have no snapshots yet) | `channel_snapshots` |
| Final snapshots per full day | 2,298–2,302 (10-05…10-07); 28,187 over 21 days | `channel_snapshots` |
| Decisions per day (all transitions) | 22–166 across 21 days, median 92; 142 on 10-07 | `signal_transitions` |
| of which NO ALERT outcomes (terminal, never alerted) | 634 in 21 days ≈ 30 a day | `signal_transitions` |
| Alerted | 0 (`ALERTED` is never reached; the worker delivers nothing) | `signal_transitions` |
| **Records per day** | **≈ 2,450** (2,302 + 142 on 10-07) | |
| Commit transaction | 79,491 gas × ≈ 103 gwei ≈ **0.0082 MON** (measured balance difference 0.0077) | receipt `0x32a6…9785` |
| Budget | 4.924 MON (faucet, human top-up only) | `cast balance` |
| Rate limit | public RPC 50 rps, 20 rps (Foundation); our need ≪ 1 rps | docs.monad.xyz |

| Design | Transactions / day | MON / day | Budget lasts | Verdict |
|---|---|---|---|---|
| One per record | 2,450 | 20.1 | **5.9 hours** | ruled out |
| One root per worker pass (5 min) | ≤ 288 | 2.4 | 2.1 days | ruled out |
| One root per 15 min | ≤ 96 | 0.79 | 6.3 days | too tight for a hackathon week |
| **One root per 30 min** | **≤ 48** | **0.39** | **12.5 days** | **chosen default** |
| One root per hour | ≤ 24 | 0.20 | 25 days | available by configuration |

The cost of batching is latency, stated plainly: a record waits for the end of its window. Its bar-close-to-block
interval is *bar close → pass that records it (≤ 5 min) → end of the window (≤ 30 min) → block*; the claim the
product makes is the measured figure for exactly that path (US5), not a promise about speed. Empty windows send
nothing, so a quiet market costs nothing.

## Constitution Check

*GATE: passed before research; re-checked after design — still passes.*

| Principle | Status |
|---|---|
| I. No look-ahead | **Engaged.** Only final records are registered; a snapshot whose `source_max_event_time_ns > as_of_ns` or whose bar is not final is refused (FR-004). The hash is computed from data already final at registration. |
| II. Time is not one thing | Record fields keep their own times; the committed `barTs` is the latest `bar_close_time` among a batch's leaves, in whole seconds; latency is `block_time − bar_close_time`, never ingest or local time. |
| III. History immutable | All four notary tables are append-only; a batch is immutable once formed (its root is its identity); a correction is a new record with a different context, hence a different hash. |
| IV, V | N/A. |
| VI. Features documented | The encoding, the tree and the bundle are documented for third parties (`contracts/notary-bundle.md`). |
| VII. Live = replay | One hashing module serves registration and verification; the same record and context give the same hash in both (tested). |
| VIII | N/A. |
| IX. No automatic execution | The service moves no value other than its own gas; it signs only `commit`. |
| X. Thresholds are configuration | Window, interval, batch cap, gas-price ceiling, minimum balance, confirmation tag, epoch, RPC, contract: all settings. |
| XI. Reproducible | This is the feature; the context is stored with every record. |
| XII. Correctness precedes performance | No optimisation; the O(N) reads the pass already does are not made worse. |
| XIII. Incremental | Snapshots and decisions only; alert links ([[REQ-INFRA-008]]) and outcomes ([[REQ-INFRA-009]]) are not started. |
| XIV. Traceable | New package carries `# @trace: REQ-INFRA-007`; tests carry the marker. |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/143-notarize-final-records/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── notary-bundle.md      # the encoding, the tree, the proof bundle: what a third party needs
└── tasks.md                  # /sdd-tasks
```

### Source Code (repository root)

```text
src/channelflow/notary/
├── __init__.py
├── scheme.py        # record hash (framing, scheme version) and the RFC 6962 SHA-256 tree + inclusion proofs; pure
├── records.py       # snapshot -> canonical row; decision row schema and derivation from a candidate's transitions
├── context.py       # NotaryContext: config hash, dataset reference, code commit (present or explicitly absent)
├── tables.py        # the four tables: schemas, appends, reads, derived outbox state
├── registrar.py     # called by the pass: registers what was just written; DecisionTracker bus subscriber
├── batcher.py       # window rule, batch formation, leaves and proofs
├── chain.py         # NotaryChain port + JSON-RPC implementation (httpx) + keystore signer (eth-account)
├── submitter.py     # send / confirm / reconcile / drain; never raises into the loop
├── verify.py        # verify a stored record or a bundle against the chain; export a bundle
├── latency.py       # per-leaf bar-close-to-block latency report
└── main.py          # `python -m channelflow.notary.main --loop`; metrics; configuration

tests/notary/        # one module per source module + the end-to-end outbox scenarios
docs/notary.md       # what is notarized, what a commit proves, the measured figure (quoted from the record)
deployments/monad-testnet-latency.json   # the measurement (written by `latency`), the only place the figure lives
```

Also touched: `src/channelflow/pipeline/channel_main.py` (pin the bars snapshot per pass; pass the registrar),
`src/channelflow/pipeline/replay.py` (an optional `on_written` hook on `ChannelRecorder`, and a bus subscription
for decisions), `src/channelflow/settings.py` (notary settings), `Dockerfile` (build args for the commit),
`docker-compose.yml` (`notary` service, secrets, worker environment), `pyproject.toml`/`uv.lock`
(`eth-account`), `.env.example`, `docs/deployment.md`, `Makefile` (a build-info target).

**Structure Decision**: a new `notary` package under `src/channelflow/`, because — unlike [[REQ-INFRA-006]]'s
deploy tooling — this runs inside the product, every day, beside the pass. The registrar is the only part the
worker imports; everything that touches the chain or the key lives behind the `notary` service.

## Design decisions, with what was rejected

1. **Decisions come from the event bus, not from the `signal_transitions` table.** Measured: 341 signals older
   than 24 hours are still `approach`/`touch`/`rejection_pending`/`confirmed` in the table (294 of them with a
   single transition). `SignalRecorder` skips every candidate that opened at or before the series watermark, so
   a candidate is written once, at first sight, and its later transitions are never appended. The spec's
   "decision = a transition row" is therefore right in meaning and wrong as a data source. A `DecisionTracker`
   subscribes to `CandidateUpdated`, remembers which `(signal_id, ordinal)` it has registered, and registers
   each new transition when it happens. *Rejected:* deriving decisions from the table (silently drops every
   terminal outcome of an already-recorded candidate, i.e. most NO ALERTs); fixing `SignalRecorder` here (a
   defect of its own, REQ-WP-0xx material, recorded in the outcome note and left alone — the notary does not
   depend on it).
2. **Register at write time, from the recorder, not by scanning the table afterwards.** `ChannelRecorder`
   already knows exactly which rows survived its watermark. A hook (`on_written`) hands them to the registrar
   after the append succeeded. *Rejected:* a scan of `channel_snapshots` for rows above a notary watermark (a
   second watermark that can disagree with the first, plus another full read per pass).
3. **The input dataset is pinned per pass.** `run_pass` reads `bars_table.current()` once, and every read in
   the pass uses that snapshot id; the pinned id and content hash are the record's dataset reference. Today
   `run_series` calls `read_bars` per series against whatever is current, and the bars table gains a snapshot
   every few seconds (14,020 so far), so without pinning no dataset reference could be true. *Rejected:*
   recording `current()` after the fact (it names data the record was not computed from).
4. **The context is stored with the record, and idempotency is by identity.** A record's identity is
   `(kind, series, timeframe, as_of or signal_id+ordinal)`. A pass that replays history and meets a registered
   identity does nothing; it never recomputes a hash with a newer dataset reference and so never produces a
   second commit for the same record (FR-006).
5. **The record's canonical bytes are the lakehouse's own.** A snapshot is `Schema.encode_row(channels.to_row(…))`
   under `channels.SCHEMA` ([[ADR-053]]); a decision is a row under a `DECISION_SCHEMA` declared in the same
   vocabulary (there is no existing table to reuse; the *encoding* is still the existing one). The context
   items are the strings `config_hash`, `dataset_reference` and the commit. The envelope is
   `"CFN" ‖ scheme_version ‖ frame(kind) ‖ frame(record) ‖ frame(config) ‖ frame(dataset) ‖ frame(commit)`,
   SHA-256, with the lakehouse's length-prefix framing. *Rejected:* JSON (the ADR-053 argument), Keccak for
   records (nothing on-chain checks them; one digest family, SHA-256, serves the records and the tree, and a
   reader needs no Keccak library).
6. **Merkle tree: RFC 6962 / RFC 9162 with SHA-256, verbatim.** Leaf `SHA256(0x00‖record_hash)`, node
   `SHA256(0x01‖l‖r)`, split at the largest power of two below n, inclusion proof per RFC 9162 §2.1.3. A published
   standard with published verification; nothing is invented. *Rejected:* duplicating the last node (the
   known second-preimage/duplicate-leaf weakness), sorted-pair trees (not a standard).
7. **Leaves are ordered `(bar_close_time_ns, kind, identity)`**, so a batch's root is a function of its set of
   records. The batch's `barTs` is the largest leaf bar-close in whole seconds; per-leaf latency is computed
   from the leaf's own bar-close, not from `barTs`.
8. **A batch is formed once and is immutable.** Its root is its identity; the leaves are written before anything
   is sent. A retry re-sends the same root. *Rejected:* re-forming a batch on retry (a different root for the
   same records orphans the first).
9. **State is derived from an append-only event log.** `notary_events` gets `formed`, `submitted(tx, nonce)`,
   `confirmed(block, block_time)`, `failed(error)`; the outbox is "batches whose latest event is not
   `confirmed`". *Rejected:* a mutable status column in Postgres (a second persistence surface that edits
   history) and files on disk (not queryable, not on the plane).
10. **Reconcile before sending, after any crash.** `commitOf(root)` first; if the contract already holds the
    root, the batch is confirmed from the chain's `Committed` log (recovering the transaction and block) and
    nothing is sent. This is what makes a crash between send and record, and a retry after a timeout, safe: the
    contract's own duplicate rejection is the final guard.
11. **Confirmed = receipt status 1 and `commitOf(root)` reads back at the `finalized` block tag.** Measured: Monad
    testnet serves `safe` and `finalized`; `finalized` trails the head by about two blocks (≈ 0.8 s).
12. **The key lives in the `notary` service only.** Compose secrets mount a keystore JSON and a password file
    read-only into that container; the worker, API and everything else never see them. The service decrypts at
    start with `eth-account`, logs only the address, and refuses to start if the address is not the contract's
    `owner()`. *Rejected:* signing inside the worker (a long-running data-pipeline process holding a key);
    an environment-variable key (FR-015).
13. **No sending below a floor.** If the balance is under `CHANNELFLOW_NOTARY_MIN_BALANCE` (or the gas price
    over `…_MAX_GAS_PRICE`) the service does not send, the outbox grows, a gauge and a log line say why.
    It never tops up.
14. **Gas limit is the estimate with a small fixed margin.** Monad charges the gas *limit* rather than the gas
    used (to be confirmed against the receipt in the first chain task); the margin is therefore a cost, and the
    measured 79,491 gas per commit is the figure the sizing used.
15. **The code commit is a build argument.** `CHANNELFLOW_CODE_COMMIT` and `CHANNELFLOW_CODE_DIRTY` are set at
    image build; absent, malformed or dirty means the registrar stores the record as unnotarizable with the
    reason (FR-010). `make notary-build-info` prints the exports so a deploy cannot forget them.
16. **No backfill.** `CHANNELFLOW_NOTARY_FROM` (an instant) sets the epoch: records with a bar close earlier are
    not registered, which also stops the first pass from registering three weeks of replayed decisions at once.
    Notarizing history is a bulk batch for a later decision, not a side effect of enabling the feature.
17. **Verification and export are commands, and the bundle needs nothing of ours.** `verify <record-id>` reads the
    stored record and recomputes; `export <record-id>` writes a bundle with the canonical bytes, the context,
    the inclusion proof, the root, the contract and the chain; `verify-bundle` needs only the bundle and a public
    RPC. `contracts/notary-bundle.md` specifies the encoding so a third party can write their own checker.
18. **The figure is stored once and quoted by test.** `latency` writes
    `deployments/monad-testnet-latency.json`; `docs/notary.md` quotes its numbers; a test compares the two and
    fails if the text claims a commit precedes a move.

## Risks

- **Existing defect found, not fixed here:** `SignalRecorder` freezes a candidate at first sight (above). Anyone
  reading `signal_transitions` or the API's signal states sees stale `approach` states for hundreds of signals.
  Recorded in the outcome note as a candidate requirement.
- **Pinning the bars snapshot changes what `run_series` reads** from "current at that moment" to "current at the
  start of the pass". Equivalent for correctness (a channel at time *t* uses only bars closed by *t*), but it is
  a change to the running pass; the first task measures the pass time before and after.
- **The pass already replays the full bar history for every series each time** (the recorders skip by
  watermark). The registrar must not add a third full read; `DecisionTracker` loads its registered-identity set
  once per pass, not per series.
- **Latency is honest and large:** minutes, not seconds, by design (sizing). The product may not claim more.
- **CI is red for an unrelated reason** (MinIO image pull); new tests run in the fast gate regardless.
- **Faucet dependence:** the 12.5-day runway is a property of one faucet claim; running out stops commits, not
  signals, visibly.
- **Rebuilding the worker image resets its start time and restart count.** Nothing is measuring those now (the
  REQ-WP-079 window closed 2026-10-04), but `--no-deps` and only the changed services remain the rule.

## Complexity Tracking

None.
