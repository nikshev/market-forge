---
description: "Tasks for REQ-WP-087 — extremum detector and channel gap policy (restart at gap)"
---

# Tasks: Extremum detector and channel gap policy (restart at gap)

**Input**: Design documents from `/specs/141-detector-gap-policy/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Written first (TDD) per spec acceptance scenarios.

**Organization**: Tasks grouped by user story for independent implementation/testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1-US5)
- Exact file paths in descriptions

## Path Conventions

- **Python**: `src/channelflow/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline metrics

- [ ] T001 Record **before**: Python test count, ETHUSDT 1h detector/channel record counts across hole

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core config and shared types — MUST complete before any user story

- [ ] T002 Add `CHANNELFLOW_GAP_THRESHOLD` to `.env.example` (default 1; 0 = any gap restarts; >1 = hole size > threshold)
- [ ] T003 Add `GAP_THRESHOLD` to `src/channelflow/config.py` (read from env, default 1)
- [ ] T004 Add `confirmation_lag_ns` field to `ExtremumRecord` in `src/channelflow/extrema/records.py`
- [ ] T005 Add `window_bars`, `window_short`, `first_bar_after_gap_ns` fields to `ChannelSnapshot` in `src/channelflow/channels/records.py`
- [ ] T006 Add gap detection helper `is_gap(prev_bar, next_bar, timeframe_ns, threshold)` in `src/channelflow/extrema/detector.py` (used by both detector and channel)

**Checkpoint**: Config, extended records, gap detection helper ready

---

## Phase 3: User Story 1 - Extremum detector restarts at gap (Priority: P1) 🎯 MVP

**Goal**: Detector resets state on hole; no confirmation straddles gap; confirmation lag only from contiguous bars

**Independent Test**: Feed detector bars with hole; verify state reset and no straddling confirmation

### Tests for US1 (write FIRST, confirm RED)

- [ ] T007 [P] [US1] `tests/extrema/test_detector_gap.py`: contiguous bars → normal tracking; 1 missing bar (threshold=1) → bridge; 2+ missing → state reset (direction=UNKNOWN, running_extreme=current, candidate=None); turn before hole + confirm after → NO confirmation emitted; confirmation lag counted only from bars after hole; no look-ahead (later bars don't change earlier record)

### Implementation for US1

- [ ] T008 [US1] `src/channelflow/extrema/detector.py`: in `run()` loop, at each bar step call `is_gap()`; if gap detected → reset `direction=UNKNOWN`, `running_extreme=current_bar`, `open_candidate=None`; skip confirmation emission if open_candidate's turn before gap and current bar after gap
- [ ] T009 [US1] `src/channelflow/extrema/detector.py`: when emitting confirmation, compute `confirmation_lag_ns = confirming_bar.close_time_ns - turn_bar.close_time_ns` and store in record

---

## Phase 4: User Story 2 - Channel fits only to bars after gap (Priority: P1)

**Goal**: Channel window starts after hole; snapshot absent/short until `lookback` contiguous bars

**Independent Test**: Feed channel bars with hole; verify window and snapshot behavior

### Tests for US2 (write FIRST, confirm RED)

- [ ] T010 [P] [US2] `tests/channels/test_channel_gap.py`: hole in series → window starts at first bar after hole; `window_bars = min(lookback, contiguous_bars_after_hole)`; `window_short = window_bars < lookback`; `first_bar_after_gap_ns` set; snapshot absent if no bars after hole; no look-ahead

### Implementation for US2

- [ ] T011 [US2] `src/channelflow/channels/window.py`: in `select_window()`, detect gap before window; if gap within last `lookback` bars → start window at first bar after gap; compute `window_bars`, `window_short`, `first_bar_after_gap_ns`; return extended snapshot data

---

## Phase 5: User Story 3 - Configuration for hole threshold (Priority: P1)

**Goal**: `gap_threshold` config (default 1); threshold=0 any gap; threshold>1 hole size > threshold

**Independent Test**: Vary threshold; verify behavior at boundary

### Tests for US3 (write FIRST, confirm RED)

- [ ] T012 [P] [US3] `tests/extrema/test_detector_gap.py` + `tests/channels/test_channel_gap.py`: threshold=1 → 1 missing = contiguous, 2+ = hole; threshold=0 → any gap restarts; threshold=2 → 2 missing = contiguous, 3+ = hole

### Implementation for US3

- [ ] T013 [US3] Already covered by T002, T003, T006 — `is_gap()` uses `GAP_THRESHOLD` from config; verify in tests

---

## Phase 6: User Story 4 - Confirmation lag in time and bars (Priority: P2)

**Goal**: Confirmed extremum carries `confirmation_lag_ns`; no straddling records on live ETHUSDT 1h

**Independent Test**: Verify confirmed extremum has both lag measures; live series zero straddling

### Tests for US4 (write FIRST, confirm RED)

- [ ] T014 [P] [US4] `tests/extrema/test_detector_gap.py`: confirmed extremum has `confirmation_lag_ns` = confirming_bar.close - turn_bar.close; `confirmation_lag_ns` > 0 and matches time diff
- [ ] T015 [P] [US4] `tests/extrema/test_live_gap_policy.py`: ETHUSDT 1h (148-bar hole) → detector/channel records before/after hole separate runs; count of straddling records = 0

### Implementation for US4

- [ ] T016 [US4] Already covered by T009 (lag_ns computation); T015 validates on live data

---

## Phase 7: User Story 5 - Live validation (Priority: P2)

**Goal**: ETHUSDT 1h (148-bar hole) shows separate runs before/after hole

**Independent Test**: Run on live bars; verify counts

### Tests for US5

- [ ] T017 [US5] `tests/extrema/test_live_gap_policy.py`: load ETHUSDT 1h bars; run detector and channel; verify records before hole end before hole, records after hole start after hole; zero records with turn before hole and confirm after hole

### Implementation for US5

- [ ] T018 [US5] No new code — validation only

---

## Phase 8: Polish & Cross-Cutting

- [ ] T019 `make lint typecheck`; all existing tests pass
- [ ] T020 `tests/extrema/test_detector_gap.py`, `tests/channels/test_channel_gap.py`, `tests/extrema/test_live_gap_policy.py` run; all pass
- [ ] T021 Outcome note; set `implemented`; `make graph && make validate`; commit with explicit paths

---

## Coverage

| requirement | task |
|---|---|
| FR-001 gap detection | T006, T007, T010 |
| FR-002 detector reset | T007, T008 |
| FR-003 no straddling confirmation | T007, T008 |
| FR-004 channel post-gap fit | T010, T011 |
| FR-005 snapshot absent/short | T010, T011 |
| FR-006 gap_threshold config | T002, T003, T012, T013 |
| FR-007 confirmation_lag_ns | T009, T014 |
| FR-008 no straddling records | T007, T008, T015, T017 |
| SC-001 detector restart | T007 |
| SC-002 channel post-gap | T010 |
| SC-003 threshold config | T012 |
| SC-004 lag_ns + no straddling live | T014, T015, T017 |
| SC-005 existing tests | T019, T020 |

---

## Dependencies

T001 first; T002-T006 any order (foundational); T007-T009 after T006; T010-T011 after T009; T012-T013 after T006; T014-T018 after T011; T019-T021 last.

## MVP

T002-T011 deliver detector reset + channel post-gap fit (US1+US2); T012-T015 add config + lag + live validation.