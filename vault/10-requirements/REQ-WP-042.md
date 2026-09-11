---
id: REQ-WP-042
title: The event backbone has an in-process implementation and a Kafka one
type: work-package
prd_ref: "§6.2, §6.3, §6.4.3, §45 Phase 8"
prd_lines: "425-438, 548-598, 6908"
phase: 8
status: implemented
depends_on: [REQ-WP-039]
tags: []
---

## Requirement

PRD §6.3 states the design in one sentence:

    MVP повинен перевірити edge, а не distributed-systems design. Але interfaces
    будуються так, щоб `EventPublisher/EventConsumer` мали in-process та Kafka
    implementations.

    (The MVP must test the edge, not distributed-systems design. But the
    interfaces are built so that `EventPublisher`/`EventConsumer` have
    in-process and Kafka implementations.)

§6.4.3 names the topics and the rules they carry:

    - schema version is explicit;
    - partition key normally `venue:symbol` or `chain:pool`;
    - event time and ingestion time are separate;
    - producer id and sequence/gap metadata are retained;
    - all consumers must be replay-safe and idempotent where materialization
      occurs;
    - raw topics may have shorter Kafka retention because canonical copies are
      persisted to S3, but retention must be long enough for operational
      replay/recovery.

[[ADR-063]] settles what was open: the broker is Redpanda on the stack, the code
is Kafka-protocol, and **the Parquet is written by a consumer in this repository
rather than by a connector or by the broker.**

**The port is the requirement, not the broker.** §6.3 asks for two
implementations behind one interface so that a change of transport is not a
change of design. An in-process bus already exists ([[REQ-WP-028]]'s
`EventBus`); what does not exist is the seam that makes it one of two.

**The rule that decides the shape** is §6.4.3's last-but-one line: consumers
must be replay-safe and idempotent where materialization occurs. This repository
already has that rule as [[ADR-056]] — every pipeline entry point reads a
per-series watermark before writing — and it exists because duplicate writes on
re-run were a real defect here. A consumer that materialises without it
reintroduces exactly that.

## Acceptance

- One publisher interface and one consumer interface, with an in-process
  implementation and a Kafka-protocol implementation behind them.
- Nothing that publishes or consumes knows which implementation it has.
- A topic name carries its schema version, per §6.4.3.
- A published event carries its partition key, its event time and its ingestion
  time as separate fields — not one timestamp doing both jobs.
- A consumer that materialises into the canonical plane goes through the same
  watermark discipline as every other entry point ([[ADR-056]]), so replaying a
  topic writes nothing twice.
- The fast gate needs no broker (REQ-INFRA-002); the Kafka path is proven
  against a real broker in CI, as the object store and the catalog are.
- Nothing existing changes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-080-event-backbone]]
- **Tests:**
    - `tests/integration/test_transport_on_redpanda.py::test_a_record_survives_the_round_trip`
    - `tests/integration/test_transport_on_redpanda.py::test_an_empty_poll_is_an_answer`
    - `tests/integration/test_transport_on_redpanda.py::test_records_come_back_in_order_within_a_key`
    - `tests/unit/transport/test_transport.py::test_a_consumer_does_not_serve_the_same_record_twice`
    - `tests/unit/transport/test_transport.py::test_a_consumer_sees_only_the_topics_it_asked_for`
    - `tests/unit/transport/test_transport.py::test_a_maker_flag_names_the_passive_side_not_the_aggressor`
    - `tests/unit/transport/test_transport.py::test_a_record_survives_the_round_trip`
    - `tests/unit/transport/test_transport.py::test_a_record_that_does_not_say_who_produced_it_is_refused`
    - `tests/unit/transport/test_transport.py::test_a_record_with_no_partition_key_is_refused`
    - `tests/unit/transport/test_transport.py::test_a_topic_without_a_schema_version_is_refused`
    - `tests/unit/transport/test_transport.py::test_an_absent_maker_flag_leaves_the_side_unknown`
    - `tests/unit/transport/test_transport.py::test_an_empty_poll_is_an_answer`
    - `tests/unit/transport/test_transport.py::test_an_ingestion_time_before_its_event_time_is_accepted`
    - `tests/unit/transport/test_transport.py::test_consuming_a_topic_twice_writes_its_rows_once`
    - `tests/unit/transport/test_transport.py::test_consuming_in_two_halves_equals_consuming_once`
    - `tests/unit/transport/test_transport.py::test_event_time_and_ingestion_time_are_two_fields`
    - `tests/unit/transport/test_transport.py::test_records_come_back_in_order_within_a_key`
    - `tests/unit/transport/test_transport.py::test_the_bar_follows_the_event_time_and_not_the_ingestion_time`
- **Code:**
    - `src/channelflow/transport/__init__.py`
    - `src/channelflow/transport/inprocess.py`
    - `src/channelflow/transport/kafka.py`
    - `src/channelflow/transport/materialise.py`
- **Outcomes:** [[OUT-2026-09-11-implement-event-backbone]], [[OUT-2026-09-11-requirement-event-backbone]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Deliberately **not** in scope, and named rather than implied:

- **Pinot.** Deferred by [[ADR-002]] until a HOT serving requirement exists. It
  is a second consumer of the same log and needs nothing from this beyond the
  topic being Kafka-protocol.
- **Schema registry.** §6.4.3 requires the schema version to be explicit, which
  a topic name carries. A registry is a different guarantee and a different
  service.
- **The full topic list.** §6.4.3 names about thirty. This builds the seam and
  the topics something already produces; a topic with no producer would be a
  name in a config file.
