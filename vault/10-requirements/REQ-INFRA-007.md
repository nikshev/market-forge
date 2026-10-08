---
id: REQ-INFRA-007
title: "Every final channel snapshot and every decision, including NO ALERT, is notarized after bar close"
type: infrastructure
prd_ref: "none -- user-directed integration, 2026-10-03; touches §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity)"
prd_lines: "0-0"
phase: null
status: planned
depends_on: [REQ-INFRA-006]
tags: [monad, notary, reproducibility]
hard_gated: false
---

## Requirement

After a bar closes, each **final** channel snapshot and each **decision** (including a decision not to
alert, `NO ALERT`) is hashed and committed through [[REQ-INFRA-006]].

The hashed record contains the snapshot or decision in its canonical encoding together with the **config
hash**, the **dataset version** (snapshot id) and the **code commit hash** — the three things
Principle XI says a result is reproducible from. Canonical encoding is the repository's existing one
(`experiments/hashing.py`'s `config_hash`; the lakehouse's content hash, [[ADR-053]]): a second encoding
would be a second definition of what the record *is*, and two drift.

The write is **asynchronous and never blocks the pipeline**: a chain outage delays notarization and is
visible, it does not delay a signal (the same rule [[REQ-WP-008]] states for Telegram).

Principle I is unaffected: the hash is computed from data already final at bar close, never earlier.

## Acceptance

- For one bar, the hash is reproducible: recomputing it from the stored snapshot, the config hash, the
  dataset snapshot id and the commit hash gives the committed value (a test, no network).
- Changing any one of the four inputs changes the hash (four tests).
- A `NO ALERT` decision is committed the same way as an alert.
- With the chain unreachable, signals are still produced and delivered, and an outbox of unsent commits
  is visible and drains when the chain returns (a test with a fake chain client).
- The interval from bar close to the commit's block time is measured on testnet and recorded; the
  product's claim is stated as that measured figure.
- Volume is sized in the plan: series × timeframes × bars a day, against the testnet's fee and rate
  limits, before the design commits to one transaction per decision.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-143-notarize-final-records]]
- **Outcomes:** [[OUT-2026-10-08-plan-notarize-final-records]], [[OUT-2026-10-08-spec-notarize-final-records]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
