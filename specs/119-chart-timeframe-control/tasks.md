---
description: "Task list for REQ-WP-074 — the timeframe is chosen on the chart"
---

# Tasks: The timeframe is chosen on the chart

**Input**: Design documents from `/specs/119-chart-timeframe-control/`

**Tests**: REQUIRED. Every Python test carries `@pytest.mark.trace("REQ-WP-074")`;
every new or changed web source file carries `// @trace: REQ-WP-074`. Write each
test first and watch it fail for the stated reason.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Backend: `src/channelflow/`, `tests/`. Frontend: `apps/web/src/`.

---

## Phase 1: Setup

- [ ] T001 Record the baseline in the implement outcome note, from the code and the running stack: `apps/web/src/App.tsx:62` reads `const timeframeNs = 15 * MINUTE_NS`; `?tf=1h` on the stack shows a heading of `1h` while the four requests carry `900000000000`; `docs/deployment.md` and `docker-compose.yml` do not mention a timeframes read

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the offered set exists end to end — vocabulary, configuration,
read, and the frontend's client for it. Every user story reads this.

- [ ] T002 Add `offered(configured)` to `src/channelflow/timeframes.py` with `# @trace: REQ-WP-074`: the union of `SOURCE_TOKEN` and `configured`, de-duplicated by token, sorted by `ns`
- [ ] T003 [P] Write the failing tests in `tests/unit/test_timeframes.py` that `offered(())` is `(1m,)`; `offered((5m, 15m, 1h))` is `(1m, 5m, 15m, 1h)` in that order; a configured list already naming `1m` yields it once
- [ ] T004 Add `timeframes: tuple[Timeframe, ...]` to `Settings` in `src/channelflow/settings.py` with `# @trace: REQ-WP-074`, parsed in `settings_from_env` through `parse_list` of `CHANNELFLOW_TIMEFRAMES`; unset means `()`
- [ ] T005 [P] Write the failing tests in `tests/unit/test_settings.py`: unset gives `()`; `"5m,1h"` gives those two in duration order; `"7m"` raises `UnknownTimeframe`; `"1M"` raises `CalendarPeriod`
- [ ] T006 Add `TimeframeOut` and `TimeframesResponse` to `src/channelflow/api/schemas.py` with `# @trace: REQ-WP-074` — `token: str`, `timeframe_ns: int`, and a tuple field named `timeframes`
- [ ] T007 Add a `timeframes: tuple[Timeframe, ...] = ()` parameter to `create_app` in `src/channelflow/api/app.py` with `# @trace: REQ-WP-074`, stored on `app.state.timeframes` beside `repository`
- [ ] T008 Pass `timeframes=settings.timeframes` from `build_app` in `src/channelflow/api/main.py` with `# @trace: REQ-WP-074`
- [ ] T009 Add `GET /api/v1/timeframes` to `src/channelflow/api/routes.py` with `# @trace: REQ-WP-074`, serving `offered(app.state.timeframes)`
- [ ] T010 [P] Write the failing tests in `tests/unit/api/test_timeframes_route.py` (new): the response carries the source plus the configured targets ascending by `timeframe_ns`; a configured `1m` appears once; an app with no configured timeframes serves `[1m]`; the JSON field is `timeframe_ns` and not a string
- [ ] T011 Add `CHANNELFLOW_TIMEFRAMES: ${CHANNELFLOW_TIMEFRAMES}` to the `api` service's environment in `docker-compose.yml`, with a comment saying both processes read one value
- [ ] T012 Add `src/timeframes.ts` (new) with `// @trace: REQ-WP-074`: `DEFAULT_TIMEFRAME = "15m"`, `interface TimeframeOption { token: string; timeframeNs: number }`, and `matchTimeframe(offered, token)` returning the exact match or `null`
- [ ] T013 [P] Write the failing tests in `apps/web/src/__tests__/timeframes.test.ts` (new): exact match; `"1H"`, `"15m "` and `"7m"` all return `null` against the real set; the default is a non-empty token
- [ ] T014 Add `fetchTimeframes` to `apps/web/src/api.ts` with `// @trace: REQ-WP-074`, returning the `timeframes` array
- [ ] T015 [P] Write the failing test in `apps/web/src/__tests__/api.test.ts` that `fetchTimeframes` requests `/api/v1/timeframes` and leaves `timeframe_ns` a number

**Checkpoint**: the set is configurable, served and reachable by the frontend. No chart change yet.

---

## Phase 3: User Story 1 — Choosing a timeframe re-reads everything at it (Priority: P1) 🎯 MVP

**Goal**: the control re-reads bars, channel, features and extrema at the chosen
duration, and the last choice wins.

**Independent Test**: render `App` with `fetch` mocked, click a second
timeframe, and assert the `timeframe_ns` on all four request URLs.

- [ ] T016 [US1] Write the failing App-level tests in `apps/web/src/__tests__/timeframeControl.test.tsx` (new): with `window.location` at `/chart/binance/BTCUSDT?tf=4h`, the bars, channel, `features/timeseries` and `extrema` requests each carry `14400000000000`; clicking `5m` re-issues all four carrying `300000000000`; the heading names the in-force token; no series request is issued before the offered set resolves
- [ ] T017 [US1] Add `src/TimeframeControl.tsx` (new) with `// @trace: REQ-WP-074`: one button per option in the given order, the selected one carrying `aria-pressed="true"`, `onSelect(token)` on click, no state of its own
- [ ] T018 [P] [US1] Write the failing tests in `apps/web/src/__tests__/TimeframeControl.test.tsx` (new): the offered tokens render as buttons in order; the selected one is marked; clicking calls `onSelect` with the token; a selected token that is not offered marks no button
- [ ] T019 [US1] Wire `App`: fetch the offered set on mount, hold the in-force token in state, take every request's duration from `matchTimeframe`, print the heading from state, and give `load` a sequence guard so a stale response is discarded (FR-012)
- [ ] T019a [P] [US1] Add regression tests in `timeframeControl.test.tsx` for FR-011: an empty `bars` answer renders `empty` (chart drawn, no failure text) and a failed answer renders `failed` (no chart drawn as empty). These pass before the change; they exist because T019 rewrites the request path and this vocabulary must not drift. No RED to watch — stated rather than fabricated
- [ ] T020 [P] [US1] Write the failing test that two clicks with promises resolved in reverse order leave the later timeframe in force — extend `timeframeControl.test.tsx` with a controlled `fetch` mock resolving out of order

**Checkpoint**: a reader can move between timeframes and the chart follows. This alone is the defect removed.

---

## Phase 4: User Story 2 — The link opens at the timeframe it names (Priority: P1)

**Goal**: `tf` is honoured on open; a link with none uses the one default; an
unhonourable token is refused visibly and no substituted request is issued.

**Independent Test**: render with `?tf=4h`, `?tf=7m`, `?tf=1M`, an unoffered
valid token, and no `tf`; assert the first request or the refusal in each case.

- [ ] T021 [US2] Change `parseDeepLink` in `apps/web/src/deepLink.ts` to default from `DEFAULT_TIMEFRAME` (imported from `./timeframes`), removing the inline `"15m"`
- [ ] T022 [P] [US2] Write the failing tests in `apps/web/src/__tests__/deepLinkQuery.test.ts` (new): no `tf` gives `DEFAULT_TIMEFRAME`; `tf=4h` is returned verbatim; a repeated `tf` returns the first
- [ ] T023 [US2] Add the refusal path to `App`: with the set loaded and no match, render a `role="alert"` naming the token and listing the offered tokens, and render no chart and issue no series request
- [ ] T024 [P] [US2] Write the failing tests in `timeframeControl.test.tsx`: `tf=7m` and `tf=1M` each produce the alert naming the token, with zero series requests; a valid token the mock set does not offer does the same and lists what is offered; a set that does not offer the default (`15m`) refuses it the same way rather than choosing a neighbour
- [ ] T025 [US2] Write the failing test that a link with no `tf` issues its first bars request at `900000000000` — the default, in one place
- [ ] T026 [US2] Make an offered-set fetch failure render `LoadState` `failed` with the detail and no chart (FR-010); cover it in `timeframeControl.test.tsx`

**Checkpoint**: every alert link this system sends opens at its own timeframe or says plainly why it cannot.

---

## Phase 5: User Story 3 — The address keeps up with the controls (Priority: P2)

**Goal**: a timeframe or mode change rewrites the query, preserving the rest of
the link, so a copy reproduces the screen.

**Independent Test**: click controls, read `window.location.search`, open the
result fresh and compare the first request with the screen's last.

- [ ] T027 [US3] Add `withTimeframe(search, token)` and `withMode(search, mode)` to `apps/web/src/deepLink.ts` with `// @trace: REQ-WP-074`: each writes exactly its own key on the current params; `withMode` deletes `as_seen_then` for AS-SEEN-THEN
- [ ] T028 [P] [US3] Write the failing tests in `apps/web/src/__tests__/deepLinkQuery.test.ts`: `withTimeframe` preserves `at`, `signal`, `chain`, `pool` and overlay keys and replaces a repeated `tf`; `withMode(..., CURRENT_REFIT)` sets `as_seen_then=false`; `withMode(..., AS_SEEN_THEN)` removes it
- [ ] T029 [US3] Call `history.replaceState` from `App`'s `onSelect` and the mode control's `onChange` using the helpers, omitting `?` for an empty query
- [ ] T030 [P] [US3] Write the failing tests in `timeframeControl.test.tsx`: clicking `30m` leaves `tf=30m` in `window.location.search` and keeps `at`/`signal`; toggling the mode sets and then removes `as_seen_then`; the address a fresh `parseDeepLink` yields carries the same timeframe the last request used

**Checkpoint**: the address bar describes the chart, in both controls.

---

## Phase 6: User Story 4 — The control offers what the deployment has (Priority: P2)

**Goal**: the offered options are what the API reported, never a frontend list.

**Independent Test**: serve a set no fixture previously used, render, and find
its tokens among the buttons.

- [ ] T031 [US4] Write the failing test in `timeframeControl.test.tsx` that a mocked set of `1m, 5m, 2h, 12h` renders those four buttons in order — tokens no source file names — and that a click on `2h` requests `7200000000000`
- [ ] T032 [P] [US4] Write the failing test that no web source file outside tests names an offered token other than the default — grep `apps/web/src` for `"1w"`, `"4h"`, `"30m"` and `"1d"` literals, excluding `__tests__` and `DEFAULT_TIMEFRAME`; the assertion is an absence, which no runtime check can see (the argument T034 of [[REQ-WP-073]] already makes)

**Checkpoint**: adding a timeframe to configuration needs no frontend change.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T033 Update `docs/deployment.md`: `GET /api/v1/timeframes` exists, what `CHANNELFLOW_TIMEFRAMES` means for the API, and that `1M` is refused. `tests/unit/docs/test_deployment_doc.py` checks every name in that file is real, so this is not optional
- [ ] T034 Run `quickstart.md` section 3 against the running stack: `/api/v1/timeframes` matches the documented JSON; `/chart/binance/BTCUSDT?tf=1h` issues `3600000000000` on all four requests; `tf=7m` refuses. Record the measured output in the implement outcome note
- [ ] T035 Run the gates: `make lint`, `make typecheck`, `make test-fast`; then `cd apps/web && npm ci && npx tsc --noEmit && npx vitest run && npx vite build` (ADR-021 — CI-only steps, run locally for this feature); then `make graph && make validate`

---

## Dependencies & Execution Order

- **Phase 2** blocks every story: no story has a duration to request without the
  offered set.
- **US1 (Phase 3)** before **US2 (Phase 4)**: the refusal path is the same state
  machine the request path builds.
- **US3 (Phase 5)** depends on US1's control existing to wire against.
- **US4 (Phase 6)** depends only on Phase 2 — it is about where the options come
  from, not about the requests — but its checkpoint assumes US1's component.
- **Phase 7** last.

### Parallel Opportunities

Every `[P]` test task is a new file or an independent block; they can be written
together. Non-`[P]` tasks each extend one module and must be sequential within
their phase.

---

## Notes

- **Write the test first and watch it fail.** Where a phase lists an
  implementation task before its test task (T002/T003, T004/T005, T006-T009/T010,
  T012/T013, T014/T015, T017/T018), the **test task runs first**: the pair is one
  change, and the list keeps each module next to its tests for readability. T016
  in particular: if it passes before T019, the mock is not capturing the
  requests.
- The Python tasks run in the fast gate. The TypeScript ones run in CI's
  `make web-test`; run them locally too (ADR-021).
- `apps/web/src/__tests__/timeframeControl.test.tsx` grows across US1–US4 by
  design: the stories are one mechanism, and splitting them across files would
  let each story's tests pass while the whole does not.
