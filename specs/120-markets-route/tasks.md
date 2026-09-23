---
description: "Task list for REQ-WP-075 — the markets route"
---

# Tasks: The markets route

**Input**: Design documents from `/specs/120-markets-route/`

**Tests**: REQUIRED. Every new or changed web source file carries
`// @trace: REQ-WP-075`; every test file is named for what it proves. Write
each test first and watch it fail for the stated reason.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Frontend: `apps/web/src/`. No backend work is planned.

---

## Phase 1: Setup

- [ ] T001 Record the baseline in the implement outcome note: visiting `/markets` on the running stack shows the placeholder ("Open a chart at /chart/&lt;venue&gt;/&lt;symbol&gt;"), because `parseDeepLink` returns `null` and `App` has no other branch; `GET /api/v1/markets` already answers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the wire shape, the client call and the two pure helpers every
story reads.

- [ ] T002 Add `MarketOut` to `apps/web/src/types.ts` with `// @trace: REQ-WP-075`: `venue`, `symbol`, `market_type` as strings and the three scores as `number | null`
- [ ] T003 [P] Write the failing test in `apps/web/src/__tests__/api.test.ts` that `fetchMarkets` requests `/api/v1/markets` with no parameters and returns the rows unchanged — including a `null` score staying `null`, not becoming `0`
- [ ] T004 Add `fetchMarkets` to `apps/web/src/api.ts` with `// @trace: REQ-WP-075`
- [ ] T005 Add `apps/web/src/markets.ts` (new) with `// @trace: REQ-WP-075`: `marketHref(venue, symbol, token)` and `scoreLabel(value)`
- [ ] T006 [P] Write the failing tests in `apps/web/src/__tests__/markets.test.ts` (new): `marketHref("binance", "BTCUSDT", "15m")` is exactly `/chart/binance/BTCUSDT?tf=15m`; a symbol needing encoding is encoded and `parseDeepLink` decodes it back; `scoreLabel(null)` is `"unscored"`; `scoreLabel(0)` is `"0.00"`; `scoreLabel(0.834)` is `"0.83"`

**Checkpoint**: the bytes of the destination and the null rule exist and are proven.

---

## Phase 3: User Story 1 — The markets list (Priority: P1) 🎯 MVP

**Goal**: `/markets` renders the API's rows in the API's order, unscored
markets plainly unscored.

**Independent Test**: stub `fetch` with a fixture whose alphabetical order
differs from its array order and whose middle row is unscored; assert the row
order and the unscored text.

- [ ] T007 [US1] Write the failing tests in `apps/web/src/__tests__/Markets.test.tsx` (new): rows render in the array's order, not alphabetically; an unscored row contains `"unscored"` and no numeric score; a scored row shows `scoreLabel`'s value; a failed read renders a `role="alert"` with the detail and **zero rows**; an empty list renders a `role="status"` saying there are no markets and **no alert**
- [ ] T008 [US1] Add `apps/web/src/Markets.tsx` (new) with `// @trace: REQ-WP-075`: fetch markets and the offered set on mount, no request depending on the other; render rows in order; the four states of `data-model.md`

**Checkpoint**: the view exists and cannot be mistaken for a failure; empty and failed are distinct.

---

## Phase 4: User Story 2 — Choosing a market and a timeframe (Priority: P1)

**Goal**: a row is a link to §27.1's deep link carrying the chosen timeframe;
the destination equals a pasted link.

**Independent Test**: read a row's `href` at the default, choose another
timeframe, read it again, and compare each with `marketHref`'s own result.

- [ ] T009 [US2] Write the failing tests in `Markets.test.tsx`: the first row's `href` is `/chart/<venue>/<symbol>?tf=<default>`; after choosing `1h` it is `/chart/<venue>/<symbol>?tf=1h`; the `href` is an `<a>`'s, so middle-click and copy work without JavaScript; a market activated after a choice lands where a hand-written link would
- [ ] T010 [US2] Render each row as `<a href={marketHref(...)}>` and hold the chosen token in the view's state, updating it from `TimeframeControl`'s `onSelect`

**Checkpoint**: overview → detail works, and the detail link is pasteable.

---

## Phase 5: User Story 3 — The root path (Priority: P2)

**Goal**: `/` and `/markets` render the view; every other unknown path keeps
the placeholder.

**Independent Test**: render `App` at the three paths and assert which view
appears.

- [ ] T011 [US3] Write the failing tests in `apps/web/src/__tests__/routing.test.tsx` (new): pathname `/` renders the markets view; `/markets` the same; `/nonsense` keeps the placeholder naming where a chart opens; `/chart/binance/BTCUSDT` still renders the chart route (FR-007)
- [ ] T012 [US3] Add the mount-stable pathname and the branch order to `apps/web/src/App.tsx` with `// @trace: REQ-WP-075`: markets first, then the deep link, then the placeholder

**Checkpoint**: the reader arriving at the host sees the product.

---

## Phase 6: User Story 4 — The offered timeframes are the deployment's (Priority: P2)

**Goal**: the control's options come from the API; its failure does not take
the rows down.

**Independent Test**: serve an unseen set and find its tokens among the
options; fail the set and find the rows still rendered with default-timeframe
links.

- [ ] T013 [US4] Write the failing tests in `Markets.test.tsx`: a set of unseen tokens renders as options **exactly** — the option list equals what the API served, so a hard-coded fallback would fail as an extra; choosing one changes every row's `href`; a failed offered-set read states the failure, offers **no options at all** (a fallback list would appear here), still renders the rows, and their `href`s carry `DEFAULT_TIMEFRAME`
- [ ] T014 [US4] Wire `TimeframeControl` from the fetched set, with the failure branch, in `Markets.tsx`

**Checkpoint**: adding a timeframe to configuration changes this view with no frontend edit.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T015 Update `docs/deployment.md`'s "Reach it" section to name `/markets` and `/` beside the chart
- [ ] T016 Run `quickstart.md` section 2 against the running stack after rebuilding the web image: `/`, `/markets` and `/nonsense` render as specified; record the measured output in the implement outcome note
- [ ] T017 Run the gates: `make lint`, `make typecheck`, `make test-fast`; `cd apps/web && npx tsc --noEmit && npx vitest run && npx vite build`; then `make graph && make validate`

---

## Dependencies & Execution Order

- **Phase 2** blocks every story: the helpers and the client are what the view
  is made of.
- **US1 (Phase 3)** before **US2 (Phase 4)**: rows must exist before their
  links can be asserted.
- **US3 (Phase 5)** is independent of US1/US2 in code (`App`'s branch) but its
  test needs `Markets` to render something identifiable.
- **US4 (Phase 6)** extends the same component; it lands after US1's state
  machine exists.
- **Phase 7** last.

### Parallel Opportunities

T003/T006 are independent test files. The remaining tasks each extend one
module and run sequentially within their phase.

---

## Notes

- **Write the test first and watch it fail.** Where a phase lists an
  implementation task before its test task (T002/T003, T004/T006, T007/T008,
  T009/T010, T011/T012, T013/T014), the **test task runs first** — the pair is
  one change, and the list keeps each module next to its tests for readability.
  T007 in particular: if the fixture is sorted alphabetically as well as by
  rank, the order assertion passes whichever way the code sorted — the fixture
  must make the two orders differ.
- No Python task is planned: no backend interface changes. `make test-fast` is
  a regression check only.
- The web gates run in CI's `make web-test` (ADR-021); run them locally too.
