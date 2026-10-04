---
description: "Tasks for REQ-WP-089 — a volume profile beside the price axis"
---

# Tasks: A volume profile beside the price axis, with buy and sell by level

**Tests** first, run RED, recorded. Phase A is deployed as soon as it passes so the data starts to accumulate.

## Phase 1: Setup

- [X] T001 Record the **before**: pytest and web counts (3,056 unit / 471 web), bundle gzip (166,906 B); no price bins exist anywhere

## Phase 2: Tests first (A: collection)

- [X] T002 [P] [US1] `tests/unit/volume/test_bins.py`: SC-001 (ten trades, hand-computed buy/sell per bin); a boundary trade belongs to the block that opens there; a late trade is discarded and counted; a price on a bin edge falls in the upper bin; unknown aggressor; the same rows for any order within the grace period; a flagged venue's block whose id span is not its trade count is dropped and counted, an unflagged venue's is written; `nice_bin_width` (1-2-5 of 2 bps) and the per-symbol override; the settings grammar (`venue:SYMBOL=width,...`: a bad entry, a non-positive width, a duplicate are refused by name)
- [X] T003 [P] [US1] `tests/unit/tables/test_volume_bins.py`: the sink writes a block once; the reader as of an instant returns only blocks closed at or before it; rows of two widths: the reader uses the latest and counts the rest
- [X] T004 [P] [US1] `tests/unit/pipeline/test_ingest_bins.py`: a fake session's trades reach the bin sink beside the bar builder; the bars are unchanged; the flush commits both
- [X] T005 Run A's tests; confirm RED for the right reasons; record the output

## Phase 3: A — collection (P1) 🎯 deployed first

- [X] T006 [US1] `src/channelflow/volume/bins.py`: `PriceBinBuilder`, `BinBlock`, `nice_bin_width`. `# @trace: REQ-WP-089`
- [X] T007 [US1] `src/channelflow/tables/volume_bins.py`: schema, `BinSink`, reader. `# @trace: REQ-WP-089`
- [X] T008 [US1] `src/channelflow/pipeline/ingest.py`, `ingest_main.py`, `src/channelflow/settings.py`: build and feed the builder beside the bar builder; flush with the bars; the two settings (`CHANNELFLOW_PROFILE_BIN_WIDTHS`, `CHANNELFLOW_PROFILE_BLOCK_SECONDS`) parsed and validated; `docker-compose.yml` passes them to the ingest services; `.env.example` and `docs/deployment.md` describe them. `# @trace: REQ-WP-089`
- [X] T009 Run A's tests green; mutation spec `tests/mutations/price_bins.toml`; **deploy `ingest-*` only** (no time-boxed measurement is running); confirm rows appear after the first block closes

## Phase 4: Tests first (B, C: the profile and the API)

- [X] T010 [P] [US2] `tests/unit/volume/test_profile_from_bins.py`: SC-002 (equals `build` for the same trades on the same grid: POC, value area, per-bin buy/sell), SC-003 (a later block changes nothing), SC-004 (coverage from 3 hours, `complete` false), one width, one bin, ties, no bins refuses
- [X] T011 [P] [US3] `tests/unit/api/test_volume_profile_route.py`: 200 with the contract's fields; 404 with a reason; 422 for another window; `at_ns` is point-in-time; the in-memory and lakehouse repositories agree
- [X] T012 Run; confirm RED; record

## Phase 5: B and C — the profile and the API (P1)

- [X] T013 [US2] `src/channelflow/volume/profile.py`: `from_bins` using the same POC and value-area tail; `src/channelflow/api/repositories.py`, `lakehouse_repository.py`: the read
- [X] T014 [US3] `src/channelflow/api/routes.py`, `schemas.py`: the route and `VolumeProfileOut`. `# @trace: REQ-WP-089`

## Phase 6: Tests first (D: the chart)

- [X] T015 [P] [US4] `apps/web/src/__tests__/profilePrimitive.test.ts`: the renderer draws one bar per bin at `priceToCoordinate(low)..(high)`, a buy part and a sell part in two colours, an unknown part in a neutral one, the POC and the value area marked, nothing for a bin outside the plot, nothing with no profile
- [X] T016 [P] [US4] `apps/web/src/__tests__/chartProfile.test.tsx` (library mocked): a primitive is attached to the candle series with the layer on and a profile, none with the layer off, replaced when the profile changes, detached on unmount
- [X] T017 [P] [US4] `apps/web/src/__tests__/profileControls.test.tsx`: the window selector (4h, 24h default, 7d) refetches; the coverage line ("covers 3 h 20 m of 24 h"); "collecting since ..." with no profile
- [X] T018 [P] `apps/web/src/__tests__/api.test.ts` additions for `fetchVolumeProfile` in a new file `volumeProfileApi.test.ts`: the request and the bigint/decimal handling
- [X] T019 Run; confirm RED; record

## Phase 7: D — the chart draws it (P1)

- [X] T020 [US4] `apps/web/src/profilePrimitive.ts`, `api.ts`, `types.ts`: the primitive, the fetch, the types. `// @trace: REQ-WP-089`
- [X] T021 [US4] `apps/web/src/Chart.tsx`, `App.tsx`: attach the primitive, the selector, the coverage line. `// @trace: REQ-WP-089`

## Phase 8: Looked at

- [X] T022 [US5] `specs/138-volume-profile/screenshots.mjs`: live BTCUSDT 15m with the profile, light and dark, into `docs/ui/profile-{light,dark}.png`; rebuild `web` and recreate `api`; **look at both**; record the coverage they show and what looking found
- [X] T023 [P] `tests/unit/web/test_volume_profile_artifacts.py`: the screenshots exist, the modules trace

## Phase 9: Polish

- [X] T024 `make lint typecheck test web-typecheck web-test web-build`; bundle gzip after
- [X] T025 Implement outcome note; set `implemented`; **one** `make graph`, then the trace `validate`; commit with explicit paths; **do not touch tracked files while the hook runs**

## Coverage

| requirement | task |
|---|---|
| FR-001 aggregate per block and bin | T002, T006, T008 |
| FR-002 incomplete blocks dropped | T002, T006 |
| FR-003 width on each row; one width per profile | T003, T007, T010 |
| FR-004 point-in-time; equals the trade-level profile | T010, T013 |
| FR-005 coverage | T010, T013, T017, T021 |
| FR-006 the API | T011, T014 |
| FR-007 the primitive | T015, T016, T020, T021 |
| FR-008 configurable width | T002, T008 |
| FR-009 live screenshots | T022, T023 |
| SC-001..SC-004 | T002, T010 |
| SC-005 existing tests | T005, T012, T019, T024 |
| SC-006 looked at | T022 |

## Dependencies

T001 first; T002-T004 any order, then T005; T006 → T007 → T008 → T009 (deploy); T010-T011 then T012; T013 → T014; T015-T018 then T019; T020 → T021; T022 after T021 and enough data; T023 after T021; T024, T025 last.

## MVP

Phase A alone starts the data; B-D make it visible.
