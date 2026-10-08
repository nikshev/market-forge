---
id: OUT-2026-10-08-spec-notarize-final-records
step: spec
records: [REQ-INFRA-007]
commit: null
---

## What was done

Specified [[REQ-INFRA-007]] as `specs/143-notarize-final-records/spec.md`: five user stories (a snapshot's hash
can be recomputed; a decision including NO ALERT goes the same way; a chain outage never delays a signal; anyone
can check a record; the claim is the measured one), eighteen functional requirements, eight success criteria.
Before writing it, six things were read from the code and the chain rather than taken from the requirement's
wording, because each one changes the shape of the feature.

## What was decided

- **The requirement's premise "after a bar closes" does not match the running system.** The worker is a periodic
  batch pass (`pipeline/channel_main.run_pass`, every `CHANNELFLOW_CHANNEL_INTERVAL`), not an event loop on bar
  close. The spec defines "after a bar closes" as "once the record is final in the lakehouse" and makes the delay
  between the two part of the measured latency instead of hiding it.
- **There is no NO ALERT record in the code.** PRD §2 promises "NO ALERT, with a reason"; nothing persists one.
  The spec defines a decision from what exists: a `signal_transitions` row, a never-alerted terminal outcome
  (`INVALIDATED`/`EXPIRED` with its reason) which *is* the NO ALERT, and a freshness-gate suppression.
  Rejected: a decision record for every series on every bar, which is the volume problem many times over and
  would mostly say "nothing happened". **This is the one assumption flagged as reversible** — it is the user's
  to overrule, because it decides what the product's silence means.
- **"One transaction per decision" cannot be afforded.** About two thousand final snapshots a day against a
  4.92 MON balance at ≈0.0077 MON per transaction (≈640 transactions in total) is roughly an order of magnitude
  over a day. The spec therefore defines *committed* as "verifiable against a value on the chain without
  trusting this system", which a batch root with published proofs satisfies as well as a direct hash, and leaves
  the choice to the plan with FR-012 forcing the sizing to be written down first.
- **The dataset version is the input, not the output.** A snapshot cannot name the snapshot of the table it is
  written into. The spec binds the bars table's snapshot id and content hash, which is also what makes a
  recomputation possible later.
- **A missing code commit makes a record unnotarizable, not blank-hashed.** The worker's container has no
  `.git`, so the commit must be injected at build; without it the record is stored as unnotarizable with the
  reason (ADR-037's rule that a component is present or explicitly absent).
- **The hash carries a scheme version and a kind.** The model artifact hash is not a fifth input (the baseline
  fits no model); if one is added it joins under a new scheme version, never silently.
- **Alerts are not delivered by the running worker at all** (`AlertGate`/`Dispatcher` are constructed nowhere
  outside `alerting/`). That does not block this feature, but it means [[REQ-INFRA-008]]'s "alert links to the
  transaction" presupposes delivery that does not yet exist; it is recorded here so it is not discovered there.

## What is still open

- **Batching versus one transaction per record, and the batch window** — the plan, from the sizing.
- **Where the outbox lives** (an Iceberg table, Postgres, a file) — the plan; it must survive restarts and be
  queryable.
- **Where the signing authority lives in a long-running container.** FR-015 fixes the rule (a mounted keystore
  and password file); how the worker reaches it, and whether signing sits in its own small process so that the
  worker never holds the key, is a plan decision with a security consequence.
- **Which settings enter the config hash** — the plan enumerates them from the channel and signal configuration.
- **The contract's `barTs` for a batch.** If a batch root is committed, what `barTs` it carries (the latest bar
  close among its leaves is the obvious choice) changes how the "within N seconds" figure is read; the plan must
  say, and the measurement must be per leaf record.
- **Top-up of the deploy account** is a human action; nothing automates it.
