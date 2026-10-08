---
id: OUT-2026-10-08-plan-notarize-final-records
step: plan
records: [REQ-INFRA-007]
commit: null
---

## What was done

Planned [[REQ-INFRA-007]] in `specs/143-notarize-final-records/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/notary-bundle.md`, `quickstart.md`. The requirement's own last acceptance line asked for the volume
to be sized before the design commits to one transaction per decision, so that was done first, from the running
system: row counts per day, per series, per timeframe and per transition state read in the worker container
(read-only), a commit's gas and price from its receipt, and Monad testnet's block tags and block spacing from
the RPC.

## What was decided

- **One Merkle root per 30 minutes, not one transaction per record.** About 2,450 records a day at ≈ 0.0082 MON
  a transaction is ≈ 20 MON a day against a 4.92 MON balance: the budget lasts 5.9 hours. A root per worker
  pass (5 minutes) lasts 2.1 days, per 15 minutes 6.3 days, **per 30 minutes 12.5 days**, per hour 25. The price
  of batching is latency, which the spec already makes the measured claim; nothing about "before the move" is
  affected. Rejected: a transaction per decision only (≈ 140 a day, 1.1 MON a day, 4.6 days) — it makes the
  rare, interesting records faster and the product's scale story worse.
- **Decisions are taken from the event bus, not the table.** The spec said "a decision is a `signal_transitions`
  row". Measured: 341 signals older than 24 hours are still `approach`/`touch`/… in that table, because
  `SignalRecorder` writes a candidate once at first sight and never appends its later transitions. The meaning
  stands; the data source does not. A `DecisionTracker` subscribes to `CandidateUpdated` and registers each new
  `(signal_id, ordinal)`. **This is a defect in an existing component that the user should know about**: the
  signals table, and anything reading it, shows stale states. It is not fixed here; it is a candidate
  requirement of its own, and the notary does not depend on its being fixed.
- **Register at write time through a hook on the recorder**, not by scanning tables afterwards (a second
  watermark that can disagree with the first, plus another full read per pass).
- **Pin the bars snapshot once per pass.** The pass reads bars per series against whatever is current, and the
  bars table gains a snapshot every few seconds (14,020 so far); no dataset reference can be true without
  pinning. A small, local change to the running pass, measured before and after.
- **The key lives only in a separate `notary` service.** The worker registers records and never touches a key
  or the chain. Rejected: signing in the worker; an environment-variable key (FR-015).
- **RFC 9162 tree with SHA-256, verbatim**, and the lakehouse's own row encoding for the record. Rejected:
  duplicating the last node (the known weakness), a home-made sorted-pair tree, JSON encoding ([[ADR-053]]'s
  argument), and Keccak for records (nothing on-chain checks them).
- **`eth-account` plus `httpx`, not `web3.py`.** The service needs nine JSON-RPC calls and one signature.
- **State is an append-only event log**, not a mutable status. Four lakehouse tables; the outbox is derived.
  Rejected: a Postgres status column (a second persistence surface that edits history).
- **Reconcile before sending**: `commitOf(root)` first, so a crash between send and record, or a retry after a
  timeout, can neither duplicate nor wedge.
- **No backfill.** An epoch setting keeps the first pass from registering three weeks of replayed decisions.

## What is still open

- **Whether Monad charges the gas limit or gas used** is documented but not shown by the existing receipts
  (limit equalled used). The first chain task sends one commit with a larger limit to measure it, because the
  answer sets the margin the service may add.
- **How the keystore reaches a uid-10001 container** (copies in a directory owned by that uid, mode 400, outside
  the repository) is described but not yet done; it is a deploy step with a security consequence and is a task
  of its own.
- **The config hash's contents** are defined as "the components' own declared fields", and the first task must
  enumerate them as they are today and fail loudly on an unhashable value.
- **The suppression kind has no live producer** (the worker delivers no alerts); its schema and tests exist,
  and the documentation says so rather than implying coverage.
- **Alert links** ([[REQ-INFRA-008]]) need an alert to exist; nothing in the running worker sends one. That
  requirement's spec should start from that fact.
- The `signal_transitions` defect above needs a decision from the user: its own requirement, or accepted.
