---
description: "Task list for REQ-WP-002 canonical domain model"
---

# Tasks: Canonical domain model

**Tests**: Included, and written first. The acceptance criterion is about
serialization behaviour, so the tests are the deliverable as much as the models.

## Phase 1: Foundations

- [x] T001 Write failing round-trip tests in `tests/unit/domain/test_round_trip.py` for `EventMeta` alone: a current-epoch `event_time_ns` survives exactly (SC-002), serializing twice is byte-identical (SC-004). Marker `@pytest.mark.trace("REQ-WP-002")`. Confirm RED.
- [x] T002 Implement `src/channelflow/domain/meta.py`: `EventMeta` with all eight PRD §9 fields, and `ChainMeta` with the four blockchain fields (FR-002, FR-003).
- [x] T003 Implement `src/channelflow/domain/serialization.py`: the encoding convention — nanosecond ints and `Decimal` as strings, deterministic key order (FR-007, FR-008, FR-009).

## Phase 2: The seven events (US1, US2)

- [x] T004 [P] `trades.py`: `TradeEvent` (FR-001, FR-004).
- [x] T005 [P] `book.py`: `PriceLevel` with zero quantity permitted, `BookDelta`, `BookSnapshot` (FR-001, FR-012).
- [x] T006 [P] `derivatives.py`: `DerivativesState` and `LiquidationEvent`, with prices as `Decimal` per ADR-003 and rates left floating (FR-004).
- [x] T007 [P] `defi.py`: `DexSwapEvent` and `DexLiquidityEvent`, each embedding `ChainMeta` (FR-003).
- [x] T008 Extend the round-trip tests to all seven kinds, including a decimal with more digits than a double holds (SC-001, SC-003).
- [x] T009 Write `tests/unit/domain/test_validation.py`: a missing required field raises and names it; a bad literal raises; assignment to a constructed event raises (FR-005, FR-006, SC-006, SC-007).

## Phase 3: Identity (US3)

- [x] T010 Add the identity each event kind needs per PRD §11.2 — CEX trade by `(venue, symbol, trade_id)`, DEX log by `(chain_id, tx_hash, log_index)` (FR-011).
- [x] T011 Write `tests/unit/domain/test_identity.py`: two events differing only in `ingest_time_ns` share an identity; changing an identity field changes it.

## Phase 4: Fixtures

- [x] T012 Generate and commit one fixture per event kind under `tests/fixtures/domain/` (FR-013).
- [x] T013 Write `tests/unit/domain/test_fixtures.py` comparing serialization against the committed bytes, and prove it is a real guard by changing a model and watching it fail (SC-005).
- [x] T014 Export the public surface from `src/channelflow/domain/__init__.py` — what a connector imports.

## Phase 5: Close

- [x] T015 `make lint`, `make typecheck`, `make test` green; `mypy --strict` must pass over the new package with no ignores.
- [x] T016 Add the `# @trace: REQ-WP-002` marker to each new source file.

## Notes

The JavaScript consumer in SC-002 is not hypothetical: PRD §27 and §28 put a
React UI on this data. The test asserts the property by parsing the serialized
form the way a double-based consumer would and comparing against the original.
