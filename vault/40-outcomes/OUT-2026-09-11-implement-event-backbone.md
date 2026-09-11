---
id: OUT-2026-09-11-implement-event-backbone
step: implement
records: [REQ-WP-042]
commit: null
---

## What was done

`channelflow/transport/`: a `Record` that carries what PRD §6.4.3 says it
carries, `EventPublisher`/`EventConsumer`, an in-process implementation and a
Kafka-protocol one, and a consumer that materialises trades through the
watermark rather than around it. Redpanda in the dev stack and in CI. 15 unit
tests and 3 integration, 10 of 10 mutants caught, 1791 tests green.

## The port is only real if one test body passes on both

The shared bodies — round trip, empty poll, ordering — live in the unit suite
and the integration suite **imports them**. Not copies: the same functions.

This is the lesson [[REQ-WP-041]] paid for, applied before it could cost
anything again: there, the claim that one catalog implementation served both
backends and the evidence for it sat in different files, and neither knew about
the other. Here the evidence is literally the same function running twice.

## A mistake of mine, and it was instructive

The first version of the integration suite patched a module-level `TRADES`
attribute to point the shared bodies at a fresh topic. It did nothing, because
`record`'s default argument was bound when the function was defined, and the
tests failed against a broker that was working perfectly.

The fix is better design rather than a better patch: the topic is a parameter
now. A shared test body that reads module state is not shared — it is two
tests that happen to look alike.

## What the sweep found

Five survivors, all rules I had written into the code and not into a test:

- **an anonymous record was accepted** — §6.4.3 asks for producer metadata, and
  without it a gap cannot be attributed to anyone;
- **the maker flag's meaning was untested** in both directions. `is_buyer_maker`
  says the *buyer* was passive, so the aggressor is the seller; inverted, every
  order-flow imbalance built on it inverts too;
- **an absent maker flag defaulting to "buy"** — the same "absent is not a
  value" failure this codebase keeps meeting, here deciding a number that feeds
  order-flow;
- **the consumer's offset was never checked** by a test, because the replay test
  used two consumers and would have passed for an implementation that never
  advanced;
- **ingestion time could replace event time** and nothing noticed. PRD §9 forbids
  a feature treating ingest time as market information, and a late record would
  have moved into the wrong window — a series that reads as a quiet minute
  followed by a busy one.

## Two smaller things worth recording

**`UNKNOWN_TOPIC_OR_PART` is not a failure.** A consumer subscribed before
anything was produced gets it, which is the case the spec calls ordinary. It is
skipped by name alongside `_PARTITION_EOF`, and every other error is raised —
because a consumer that dropped errors would report an empty poll, and an empty
poll reads as "nothing happened".

**The integration env helper read one file and stopped.** `.env` won over
`.env.example`, so adding `REDPANDA_PORT` to the example left every existing
checkout with a `KeyError` instead of a message. It now reads the example as
defaults and `.env` as overrides, which is what those two files mean.

## What is still open

- **One materialising consumer**, for trades. §6.4.3 names about thirty topics;
  a topic with no producer would be a name in a config file.
- **Pinot** is a second consumer of the same log and is deferred by [[ADR-002]].
- **Delivery semantics.** The watermark makes materialising idempotent, so
  at-least-once is enough; whether anything ever needs more is a question for
  whoever runs it.
