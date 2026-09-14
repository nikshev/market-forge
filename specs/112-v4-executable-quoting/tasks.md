---
description: "Task list for REQ-WP-071 — CUSTOM_ACCOUNTING pools are quoted, never curved"
---

# Tasks: CUSTOM_ACCOUNTING pools are quoted, never curved

**Input**: Design documents from `/specs/112-v4-executable-quoting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED. This repository's ladder passes through `tested` before
`implemented`, and every test carries `@pytest.mark.trace("REQ-WP-071")`. Write
each test first and see it fail for the stated reason before writing code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US6 from spec.md

## Path Conventions

Single project: `src/channelflow/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: nothing to install. The fixture is already captured and committed.

- [ ] T001 Confirm `tests/fixtures/uniswap_v4/quotes.jsonl` holds 24 records at block 25975796 — 1 `quoter`, 4 `state`, 16 forward ladder rungs, 3 reverse answers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the replay seam and the shared ABI machinery. Every story's test
needs these.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete

- [ ] T002 Add `CallReverted(RuntimeError)` with `data: str | None` beside `NoHealthyProvider` in `src/channelflow/chain/providers.py`, documenting that `None` means "this endpoint did not say", not "reverted with nothing"
- [ ] T003 Create `src/channelflow/dex/v4_quoting.py` with the module docstring, `# @trace: REQ-WP-071`, and selectors computed at import from their signatures — `quoteExactInputSingle(...)`, `poolManager()`, `UnexpectedRevertBytes(bytes)`, `NotEnoughLiquidity(bytes32)`, `PriceLimitAlreadyExceeded(uint160,uint160)`
- [ ] T004 [P] Write the failing test for the call encoder in `tests/unit/dex/test_v4_quoting.py`: encoding pool `0xf7caa8ee…` at 1e18 `zero_for_one` produces call data whose first four bytes are the computed selector, whose head word is 32, and whose `tick_spacing` word is the full 256-bit sign extension of 200
- [ ] T005 Implement `encode_exact_input_single(key, *, zero_for_one, exact_amount)` in `src/channelflow/dex/v4_quoting.py` until T004 passes
- [ ] T006 [P] Write the failing tests for `ReplayProvider` in `tests/unit/dex/test_v4_quoting.py` (the provider itself will live in `tests/unit/dex/replay_provider.py`): it answers `eth_call` from `quotes.jsonl` keyed on `(to, calldata)` built with the adapter's own encoder, raises `CallReverted` carrying the captured payload for refusal records, raises `QuoteNotCaptured` for anything else, and never returns `"0x"`
- [ ] T007 Implement `ReplayProvider` in `tests/unit/dex/replay_provider.py` until T006 passes, serving `poolManager()` for the quoter and state-view addresses from the fixture header

**Checkpoint**: the fixture is reachable through the real `ChainDataProvider`
protocol, and CI can exercise the encoder offline.

---

## Phase 3: User Story 1 — The curve refuses these pools (Priority: P1) 🎯 MVP

**Goal**: no `CUSTOM_ACCOUNTING` pool can obtain a depth figure from the tick
kernel.

**Independent Test**: `require_curve_applies` raises for all four fixture pools
and returns for a `STANDARD_CL` key.

- [ ] T008 [P] [US1] Write the failing regression test in `tests/unit/dex/test_v4_quoting.py` proving what happens without the gate: a `PoolState` built from the fixture's `state` record for `0xf7caa8ee…` passes `require_tick_map_complete`, and `depth_to_bps(bps=Decimal(50), upward=True)` returns `reachable is False`, `amount0 == 0`, `amount1 == 0`, reason exactly `"the pool has no active liquidity, so its price cannot be moved"` — while the fixture's 1e18 quote for the same pool at the same block is `496412035653451820217981817`
- [ ] T009 [P] [US1] Write the failing test for the gate in `tests/unit/dex/test_uniswap_v4.py`: `require_curve_applies` raises `CurveDoesNotApply` for each of the four fixture pools' keys and for a `UNKNOWN` key, and returns `None` for `STANDARD_CL`, `DYNAMIC_FEE_CL` and `HOOK_AUGMENTED_CL` keys taken from the same fixture
- [ ] T010 [US1] Add `CURVE_RECONSTRUCTIBLE`, `CurveDoesNotApply` and `require_curve_applies(key)` to `src/channelflow/dex/uniswap_v4.py` until T009 passes — a permit list, not a deny list, with the refusal message naming the class and the pool id
- [ ] T011 [US1] Export the three new names from `src/channelflow/dex/__init__.py`

**Checkpoint**: the gate exists and the hazard it guards is pinned by an
asserted regression.

---

## Phase 4: User Story 2 — A quote is executable, sized and dated (Priority: P1)

**Goal**: a quote that carries what it is a quote *of*.

**Independent Test**: every forward rung in the fixture decodes to its captured
`amount_out` and `gas_estimate`.

- [ ] T012 [P] [US2] Write the failing test in `tests/unit/dex/test_v4_quoting.py` that `QuoteRequest` rejects `exact_amount == 0` and negative amounts with `ValueError`
- [ ] T013 [P] [US2] Write the failing table test asserting all 12 successful forward rungs decode to their exact captured `amount_out` and `gas_estimate` — literal integers, no tolerance, no `>` comparisons
- [ ] T014 [P] [US2] Write the failing test that `Quote.block` equals 25975796 for every answer, and that a `Quote` with `amount_out == 0` cannot be constructed
- [ ] T015 [P] [US2] Write the failing test that `implied_price` puts both directions of `0x88249e68…` in the same units and that they are **not** equal: buying gives `746527124.6970774645442279` `currency1` per `currency0`, selling costs `760969961.257573001614822577892706206184793472934` — a gap of `0.0193467003176288987269066952` relative, which is the round-trip cost, and the sell price is the worse of the two. Assert the direction of the inequality as well as the figures; a test that only checked "close" would pass with the two sides swapped
- [ ] T016 [US2] Implement `QuoteRequest`, `Quote`, `implied_price` and `ExecutableQuoter.quote` in `src/channelflow/dex/v4_quoting.py` until T012–T015 pass

**Checkpoint**: the happy path replays exactly.

---

## Phase 5: User Story 3 — A refusal is a named outcome (Priority: P1)

**Goal**: seven captured refusals, decoded by name, never as a number.

**Independent Test**: the two distinct reasons are told apart and the pool id
inside `NotEnoughLiquidity` matches the pool asked about.

- [ ] T017 [P] [US3] Write the failing test that quoting `0x5ce617f9…` at each of 1e15, 1e16, 1e17 and 1e18 raises `QuoteRefused` with `reason is RefusalReason.NOT_ENOUGH_LIQUIDITY` and `named_pool_id == "0x5ce617f9e436c9e71c6de6306bc5a466fe2ef4145649d6b5ef9aa8a27ed530c1"`
- [ ] T018 [P] [US3] Write the failing test that the reverse quote on `0x5d10cbe0…` raises `QuoteRefused` with `reason is RefusalReason.PRICE_LIMIT_ALREADY_EXCEEDED`, and that both decoded arguments equal `1461446703485210103287273052203988822378723970341`, which is also that pool's `state` record's `sqrt_price_x96`
- [ ] T019 [P] [US3] Write the failing test that an unrecognised inner selector decodes to `RefusalReason.UNKNOWN` with `raw` preserved byte for byte — and specifically that it does **not** decode to `NOT_ENOUGH_LIQUIDITY`
- [ ] T020 [P] [US3] Write the failing test that a payload which is not `UnexpectedRevertBytes` at all, and a `CallReverted` with `data is None`, both give `RefusalReason.UNKNOWN` rather than raising a decoding error
- [ ] T021 [P] [US3] Write the failing test that a provider raising a transport error gives `QuoteUnavailable`, and that `QuoteUnavailable` is not a subclass of `QuoteRefused` in either direction
- [ ] T022 [P] [US3] Write the failing test that `quote` issues exactly one `eth_call` for a refused request — no retry at a smaller size, no retry at another block — by counting calls on a recording provider
- [ ] T023 [US3] Implement `RefusalReason`, `decode_refusal`, `QuoteRefused`, `QuoteUnavailable` and the refusal path of `ExecutableQuoter.quote` until T017–T022 pass

**Checkpoint**: every refusal in the fixture is named, and none of them is zero.

---

## Phase 6: User Story 4 — One side is not a market (Priority: P1)

**Goal**: no mid where the chain gives only one side.

**Independent Test**: the two one-sided pools raise; the two-sided one returns a
number.

- [ ] T024 [P] [US4] Write the failing test that `mid` on `0xf7caa8ee…` and on `0x5d10cbe0…` raises `NoTwoSidedMarket` whose `__cause__` is the `QuoteRefused` from the refusing side
- [ ] T025 [P] [US4] Write the failing test that `mid` on `0x88249e68…` returns the geometric mean of the two directions' `implied_price`, asserted against a literal `Decimal` computed from the fixture's own two amounts
- [ ] T026 [P] [US4] Write the failing test that `mid` issues exactly two `eth_call`s, both at the adapter's block
- [ ] T027 [US4] Implement `NoTwoSidedMarket` and `ExecutableQuoter.mid` until T024–T026 pass

**Checkpoint**: a one-sided pool yields an exception, not a halved number.

---

## Phase 7: User Story 5 — The quoter must name the manager (Priority: P2)

**Goal**: the address is verified, not recalled.

**Independent Test**: a quoter naming another manager is refused before any
quote.

- [ ] T028 [P] [US5] Write the failing test that `verify()` returns for the fixture's quoter and raises `WrongQuoter` when the provider's `poolManager()` answers a different address, with the message naming both
- [ ] T029 [P] [US5] Write the failing test that `WrongQuoter` is raised before any quoting `eth_call` is issued, counted on a recording provider
- [ ] T030 [US5] Implement `WrongQuoter` and `ExecutableQuoter.verify` until T028–T029 pass

**Checkpoint**: identity is established by measurement.

---

## Phase 8: User Story 6 — Replay is the same code (Priority: P1)

**Goal**: one code path; CI proves it offline.

**Independent Test**: the suite passes with no network access, through the same
encoder and decoder the live provider would drive.

- [ ] T031 [P] [US6] Write the failing test that `ExecutableQuoter` contains no branch on provider type: assert the adapter's own module imports nothing from `tests/` and nothing named `Replay`, by inspecting `src/channelflow/dex/v4_quoting.py`'s imports
- [ ] T032 [P] [US6] Write the failing test that a request absent from the fixture raises `QuoteNotCaptured` and never yields `amount_out == 0`
- [ ] T033 [P] [US6] Write the failing test that every `eth_call` the adapter issues names the adapter's own block — asserted on a recording provider that captures the `block` argument — so an answer from a later block can never be served as this quote
- [ ] T033a [US6] Confirm the whole new test module runs under `pytest -m "not integration"` with no network — no `urllib`, no sockets, no `tools.record` import

**Checkpoint**: Constitution VII is demonstrated, not asserted.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T034 `make lint && make typecheck` clean — `mypy --strict` over `src/`
- [ ] T035 Run `.venv/bin/python tools/mutate.py` over `src/channelflow/dex/v4_quoting.py` and the new functions in `uniswap_v4.py`; every survivor is a weak assertion to strengthen, not a mutation to suppress
- [ ] T036 Write the mutation specification section into the implement outcome note, listing each survivor found and the assertion that killed it
- [ ] T037 Run through `specs/112-v4-executable-quoting/quickstart.md` end to end
- [ ] T038 `make graph && make validate` clean; requirement reaches `implemented`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: no dependencies
- **Foundational (T002–T007)**: blocks every story — the replay provider is how
  all six are tested
- **US1 (T008–T011)**: independent of the adapter; only needs the fixture
- **US2 (T012–T016)**: needs Foundational
- **US3 (T017–T023)**: needs Foundational and T016's `quote` skeleton
- **US4 (T024–T027)**: needs US2 and US3 — a mid is two quotes, either of which
  may refuse
- **US5 (T028–T030)**: needs Foundational only
- **US6 (T031–T033a)**: needs everything else to be meaningful
- **Polish (T034–T038)**: last

### Within Each User Story

Tests first, seen failing for the stated reason, then the code. Models before
services. No implementation task precedes its test task.

### Parallel Opportunities

- T004 and T006 (different files)
- T008 and T009 (different files)
- All of T012–T015 (all test-writing in one file, but independent functions —
  serialise if the same file is a conflict)
- All of T017–T022
- T024–T026, T028–T029, T031–T033

---

## Implementation Strategy

### MVP (US1 alone)

T001 → T008–T011. That alone closes the hole PRD §18.8.1 names: after it, no
`CUSTOM_ACCOUNTING` pool can be handed a depth figure. It delivers a refusal
rather than a price, which is a smaller thing than the requirement asks for and
strictly better than today's confident zero.

### Incremental delivery

1. Foundational → the fixture is reachable through the real protocol
2. US1 → the curve is closed off (MVP)
3. US2 → pools have prices
4. US3 → refusals have names
5. US4 → one-sided pools have no mid
6. US5 → the quoter is verified
7. US6 → replay parity is demonstrated

---

## Notes

- Mutation testing is the acceptance standard here: assertions pin exact
  integers taken from the fixture. A test asserting `amount_out > 0` would
  survive nearly every mutation and prove nothing.
- The one thing this plan cannot make impossible is a future v4→`PoolState`
  bridge that skips the gate. T008 exists to make that hazard visible.
