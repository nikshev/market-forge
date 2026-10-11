---
description: "Tasks for REQ-WP-096 -- the venue-basis pane has a consensus"
---

# Tasks: The venue-basis pane has a consensus

**Input**: `spec.md`, `plan.md`. Needs spec 147's quotes. Tests first.

## Phase 1: Registry and fixtures

- [X] T001 Confirm the asset registry maps `bybit BTCUSDT` and `okx BTC-USDT-SWAP` to one asset with market type perp, and Binance spot BTC/ETH/SOL to their own; add the mapping as data with a test if not

## Phase 2: Tests (RED first)

- [X] T002 [P] `tests/unit/crossvenue/test_consensus_write.py`: two and three venues -> median; one venue -> refusal row with reason and no price; stale and later quotes excluded with a reason; later quotes appended -> earlier close identical; idempotent re-run; a gap -> refusal rows; a lagging venue holds the pass back (the minimum of the contributing venues' newest quote times)
- [X] T003 [P] `tests/unit/api/test_venue_basis_from_written.py`: a stored output read back through `select_venue_basis` equals `10000 * (mid / consensus - 1)`; the Binance read returns the reason
- [X] T004 [P] `tests/mutations/consensus_write.toml`

## Phase 3: Implementation

- [X] T005 `crossvenue/consensus_write.py`; `tables/consensus.py` read of the watermark; one call in `pipeline/channel_main.py`
- [X] T006 `docs/deployment.md`

## Phase 4: Gate and live evidence

- [X] T007 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T008 No-write replay on real quotes (after spec 147 has produced a day); after deploy the recorded reads for SC-004

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001-005 pass, refusals, registry, watermark | T001-T003, T005 |
| FR-006/007 read-time merge, single writer | T003, T005 |
| SC-001/002 | T002 |
| SC-003 | T002 |
| SC-004 | T008 |
| SC-005 | T002 |
