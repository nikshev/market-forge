# Implementation Plan: Canonical domain model

**Branch**: `004-domain-model` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

## Summary

Seven frozen Pydantic v2 models for PRD §10's canonical events, each embedding
`EventMeta`, with `Decimal` for money and string encoding for nanosecond
timestamps. Proven by property tests and committed fixtures.

## Technical Context

**Language/Version**: Python 3.12, strict mypy.

**Primary Dependencies**: Pydantic v2 (PRD §7). No other new dependency.

**Storage**: none. This feature defines shapes; nothing is written anywhere.

**Testing**: pytest. Round-trip and rejection tests are pure; fixture tests
compare against committed bytes.

**Target Platform**: library code under `src/channelflow/domain/`.

**Project Type**: library module inside the existing package.

**Performance Goals**: none stated. Pydantic v2 validation is fast enough that
measuring it here would be premature; PRD §36's targets concern ingestion
throughput, which is a later work package's problem.

**Constraints**: FR-007 and FR-008 — the encoding must survive a consumer that
parses JSON numbers as doubles. That is the constraint the whole feature exists
to honour.

**Scale/Scope**: nine model types (seven events, plus `EventMeta`, `ChainMeta`,
`PriceLevel`), one serialization convention, seven fixtures.

## Constitution Check

Binding here, and more of it than usual — this is the feature where the
constitution's time rules become code:

- **II (time is not one thing)** — `EventMeta` carries `event_time_ns` and
  `ingest_time_ns` as separate, both-required fields. The whole point of
  ADR-003's embedding decision is that neither can be quietly omitted, which is
  what makes §0.4's prohibition on conflating them checkable at all.
- **III (history is immutable)** — models are frozen. An event that has been
  constructed cannot be edited into saying something else.
- **XI (results are reproducible)** — FR-009's byte-identical serialization is
  what makes a fixture a fixture. Without it, "the output changed" and "the
  output was written twice" are indistinguishable.
- **XII (correctness precedes performance)** — `Decimal` over `float`
  throughout, and string encoding over numeric, both trading speed for exactness.
- **XIV (everything is traceable)** — this feature traces to REQ-WP-002.

**Principle I (no look-ahead)** does not bind directly: these models carry
timestamps but compute nothing. It binds every feature built on them, which is
why `ingest_time_ns` must be present and distinct here.

**Gate result: PASS.** No violations; Complexity Tracking empty.

## Project Structure

```text
src/channelflow/domain/
├── __init__.py          # public surface: what a connector imports
├── meta.py              # EventMeta, ChainMeta
├── book.py              # PriceLevel, BookDelta, BookSnapshot
├── trades.py            # TradeEvent
├── derivatives.py       # DerivativesState, LiquidationEvent
├── defi.py              # DexSwapEvent, DexLiquidityEvent
└── serialization.py     # the encoding convention and its round trip

tests/unit/domain/
├── test_round_trip.py   # SC-001 to SC-004
├── test_validation.py   # SC-006, SC-007
├── test_identity.py     # FR-011
└── test_fixtures.py     # SC-005

tests/fixtures/domain/   # seven committed JSON files
```

**Structure Decision**: split by subject, not by layer — a connector working on
order books imports one module. `serialization.py` is separate because the
encoding convention is the thing most likely to need changing, and it should be
changeable in one place rather than seven.

**Deliberately not produced**: no `data-model.md`. The models *are* the data
model, they are typed, and a prose copy would drift from them within a week.
No `contracts/` — nothing serves anything yet.

## Complexity Tracking

> No violations.
