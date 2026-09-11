# Implementation Plan: The event backbone

**Branch**: `wp-042-event-backbone` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

`channelflow/transport/`: a `Record`, two ports, two implementations, and one
materialising consumer that reuses the watermark rather than repeating it.

## Technical Context

**Language**: Python 3.12 · **New dependency**: `confluent-kafka`

**Testing**: one parametrised test body over both transports; a replay test that
consumes a topic twice; an integration test against Redpanda in CI.

**Constraints**: the fast gate needs no broker; nothing existing changes.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VII. Live and replay are the same code** | The seam is the whole point: one interface, two transports. | **Pass.** |
| **V. Append-only** | The materialising consumer goes through [[ADR-056]]'s watermark. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-042`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/transport/__init__.py        # NEW: the ports and the record
src/channelflow/transport/inprocess.py       # NEW
src/channelflow/transport/kafka.py           # NEW
src/channelflow/transport/materialise.py     # NEW: trades -> the canonical plane
docker-compose.yml                           # + redpanda
.env.example                                 # + REDPANDA_PORT
tests/unit/transport/test_transport.py       # NEW: one body, both transports
tests/integration/test_transport_on_redpanda.py  # NEW
```

## One test body, two transports

The port is only real if the same test passes against both, so the unit suite
parametrises over a factory. The in-process transport runs everywhere; the Kafka
one runs where a broker is, which is the integration suite.

A test written against one implementation and read as proof of the interface is
the failure this arrangement prevents — the same shape as
[[REQ-WP-041]]'s catalog, where the claim and its evidence sat in different
files and neither knew.

## The materialising consumer reuses, and does not repeat

`record_bars` already aggregates trades and writes the bars a table does not
have, reading a per-series watermark first ([[ADR-056]]). The consumer decodes
records into `TradeEvent`s and hands them to it.

That is the whole design, and it is deliberately thin: the moment this module
knew how to write a table, there would be two entry points to the canonical
plane and one of them would eventually forget the watermark. [[ADR-063]] refused
a connector for exactly that reason; building one here in Python would be the
same mistake in a friendlier language.

## The record's rules, enforced at construction

- the topic must end in `.vN` — §6.4.3's explicit schema version, checked rather
  than hoped for;
- the partition key must be present, because ordering is per key and a record
  without one has no ordering guarantee to lose;
- event time and ingestion time are two fields, never one. PRD §9 forbids a
  feature treating ingest time as market information, and a single timestamp
  would leave nothing downstream to tell them apart.

An ingestion time earlier than its event time is **accepted**. Clocks disagree;
a transport that quietly repaired the disagreement would hide it from the only
people who could fix it.
