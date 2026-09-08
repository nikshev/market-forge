---
description: "Task list for REQ-WP-006 channel baseline"
---

# Tasks: Channel baseline

**Tests**: Written first. Pure — no services.

## Phase 1: No look-ahead (US1)

Deliberately first. If this cannot be made to hold, nothing else is worth
building.

- [x] T001 Write failing tests in `test_no_lookahead.py`: refitting at an unchanged `as_of` after appending later bars gives an identical snapshot; `source_max_event_time <= as_of` always; bars after `as_of` are excluded; unfinalized bars are excluded (SC-001, SC-002, FR-007-FR-009). Marker `@pytest.mark.trace("REQ-WP-006")`. Confirm RED.
- [x] T002 Implement `models.py`: frozen `ChannelSnapshot` and `ChannelQuality` with the PRD §13.1 fields (FR-006, FR-015).
- [x] T003 Implement the `as_of` filter and the invariant check in `rolling_ols.py`, before any fitting logic (FR-007, FR-008, FR-009).

## Phase 2: The fit (US2)

- [x] T004 Write failing tests in `test_fit.py`: a constructed log-linear slope is recovered; two price levels of the same shape give equal normalized slopes; bands sit at the configured residual quantiles; insufficient history and a non-positive close each refuse with a message (SC-003, SC-004, SC-008, FR-010, FR-011). Confirm RED.
- [x] T005 Implement the OLS fit on log close, the centre as its exponential, and the residual-quantile bands (FR-001-FR-003).
- [x] T006 Implement `slope_normalized` per ADR-007 and `width_pct` (FR-004, FR-005).
- [x] T007 Handle the degenerate case where residuals vanish — bands collapse onto the centre without dividing by zero.

## Phase 3: Quality (US3)

- [x] T008 Write failing tests in `test_quality.py`: coverage on a well-behaved series is near the band width; a clean trend outscores noise; the score names its contributors; an unavailable submetric is omitted, not defaulted (SC-005-SC-007, FR-012-FR-014). Confirm RED.
- [x] T009 Implement the six submetrics in `quality.py`, each documented with what it measures and its units (FR-012).
- [x] T010 Implement the weighted average with configurable weights, omitting unavailable submetrics (FR-013, FR-014).

## Phase 4: Close

- [x] T011 Verify FR-016 — determinism — by fitting twice and comparing.
- [x] T012 Mutation-check the invariant: remove the `as_of` filter and confirm a test fails. This is the one that matters; a passing suite that would survive its removal proves nothing.
- [x] T013 Add `# @trace: REQ-WP-006` to each new source file.
- [x] T014 `make lint`, `make typecheck`, `make test` green.

## Notes

Phase 1 comes before the fit on purpose. The usual order would build the model
and then guard it; here the guard is the product requirement and the model is
the detail.
