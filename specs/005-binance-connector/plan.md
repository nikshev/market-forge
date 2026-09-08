# Implementation Plan: Binance connector

**Branch**: `wp-003-binance-connector` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Three separable pieces: a pure normalizer from venue message to canonical event,
a pure order-book reconstruction with an honest health state, and a thin
lifecycle around a websocket. The first two are the correctness surface and are
tested against 105 recorded messages; the third is transport.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `websockets` for transport; the domain models from
REQ-WP-002. No exchange library — ADR-004.

**Storage**: none. The connector emits events; persisting them is later work.

**Testing**: pytest against committed fixtures. No socket opens in any test
(FR-018, SC-008), which is what keeps the connector inside the fast gate rather
than needing the CI-only gate from REQ-INFRA-002.

**Target Platform**: library code under `src/channelflow/connectors/binance/`.

**Project Type**: library module.

**Performance Goals**: none stated here. PRD §36's ingestion targets bind a
later work package; measuring a normalizer before there is a pipeline to feed
would be premature.

**Constraints**: FR-004 — the venue clock and our clock must stay apart. Every
other requirement is recoverable from; conflating those two silently corrupts
every downstream claim about ordering.

**Scale/Scope**: three modules plus their tests, against 105 recorded messages.

## Constitution Check

- **I (no look-ahead)** — binds directly here for the first time. The connector
  is where `event_time` is assigned, and every later guarantee inherits whatever
  it decides. FR-004 and SC-003 are that principle made checkable.
- **II (time is not one thing)** — three venue-side clocks reduced to two
  fields, deliberately, with the discarded one recorded in the spec's
  Assumptions rather than dropped silently.
- **VII (live and replay are the same code)** — the normalizer and the book take
  messages, not sockets. A replayed fixture and a live frame follow the same
  path, which is the only way §35.6's replay tests prove anything about live
  behaviour.
- **VIII (connectors share one interface)** — this is the first connector, so
  the interface is being set rather than followed. Kept deliberately small: a
  normalizer function per message kind, and a book that accepts deltas.
- **XI, XIV** — fixtures are committed and the feature traces to REQ-WP-003.

**Gate result: PASS.** Complexity Tracking empty.

## Project Structure

```text
src/channelflow/connectors/
├── __init__.py
└── binance/
    ├── __init__.py
    ├── normalize.py     # venue message -> canonical event. Pure.
    ├── orderbook.py     # PRD §11.1 reconstruction + BookHealth. Pure.
    └── session.py       # websocket lifecycle, keepalive, reconnect, counters

tests/unit/connectors/binance/
├── test_normalize.py    # SC-001 to SC-003
├── test_orderbook.py    # SC-004 to SC-006
└── test_session.py      # SC-007, with a fake clock and fake transport
```

**Structure Decision**: the split is the point. `normalize.py` and
`orderbook.py` contain every rule that can be wrong in a way that corrupts data,
and neither imports a socket. `session.py` holds what cannot be tested without
one, and is kept as thin as that division allows.

**Not produced**: no `data-model.md` — the canonical models are REQ-WP-002's and
are typed. No `contracts/` — nothing is served.

## Complexity Tracking

> No violations.
