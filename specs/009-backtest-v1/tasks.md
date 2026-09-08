---
description: "Task list for REQ-WP-010 backtest v1"
---

# Tasks: Backtest v1

**Tests**: Written first. Pure.

## Phase 1: Parity (US1)

First, because it is the requirement. If replay cannot match live, the rest is
a report about the wrong thing.

- [x] T001 Write failing `test_parity.py`: driving `SignalMachine` directly over a bar series and running the backtest over the same series give identical candidate histories, transition for transition (SC-001). Marker `@pytest.mark.trace("REQ-WP-010")`. Confirm RED.
- [x] T002 Implement `runner.py`: walk bars in event-time order, fit a channel at each with `as_of` set to that bar, drive the machine (FR-001, FR-002, FR-004).

## Phase 2: The report (US2)

- [x] T003 Write failing `test_report.py`: candidate counts by direction and boundary; confirmation rate and terminal reasons; the configuration is named; skipped bars are reported; no economic metric appears (SC-004-SC-007). Confirm RED.
- [x] T004 Implement `report.py`: a frozen report carrying counts, rates, configuration, time range and skipped bars (FR-007-FR-011, FR-013).
- [x] T005 Assert FR-012 mechanically: a test over the report's own field names, so adding a `win_rate` field later fails until ADR-009 is revisited.

## Phase 3: Virtual clock (US3)

- [x] T006 Write failing `test_virtual_clock.py`: two runs over the same input give identical reports; no backtest module references a system clock (SC-002, SC-003). Confirm RED.
- [x] T007 Verify the clock property over the source, as the bar builder does.

## Phase 4: Close

- [x] T008 Mutation-check: give the runner its own inlined transition rule and confirm the parity test fails.
- [x] T009 Add `# @trace: REQ-WP-010` to each new source file.
- [x] T010 `make lint`, `make typecheck`, `make test` green.

## Notes

T005 is unusual and deliberate. ADR-009 says the report carries no economic
metric; a test over the field names turns that from a decision someone might
forget into one they must actively revisit.
