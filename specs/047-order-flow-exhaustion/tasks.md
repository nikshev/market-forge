---
description: "Task list for REQ-EXP-014"
---

# Tasks: Order-flow exhaustion around extrema

- [x] T001 Write failing tests for the shape: six bullets, both arms per signal, the retrospective declaration (SC-001, SC-002).
- [x] T002 Implement the conditional arm: straddling window, control gap, effect size (FR-001 to FR-003).
- [x] T003 Implement the predictive arm: trailing threshold, full horizon, absent precision (FR-004 to FR-008).
- [x] T004 Implement the reading rule and the report's list of signals that explain without forecasting (FR-010, FR-011).
- [x] T005 Export it from `channelflow.research` and add the trace marker.
- [x] T006 Mutation-check fifteen guards with the bounded runner, verifying every restore.
- [x] T007 Close the three the sweep found: the threshold's provenance, the horizon's last bar, and precision over no calls.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T001, T002 |
| FR-002, FR-003 | T002 |
| FR-004 | T003, T007 |
| FR-005, FR-006 | T003 |
| FR-007, FR-008 | T003, T007 |
| FR-009 | T001 |
| FR-010, FR-011 | T004 |
| FR-012 to FR-014 | T002, T003 |
| SC-001, SC-002 | T001 |
| SC-003 | T002 |
| SC-004, SC-007, SC-008 | T007 |
| SC-005, SC-006 | T003 |
| SC-009 to SC-012 | T004 |
| SC-013 to SC-015 | T002, T003 |

## Notes

Two of the survivors in T007 were the same failure twice: a fixture whose halves
look alike cannot tell a trailing quantile from a whole-series one, because both
land on the same number. The look-ahead test now runs on a series whose second
half sits a hundred times higher than its first.

The third was the horizon's own last bar. Losing it costs the study the calls
furthest ahead of each turn — the ones a forecast is actually worth something
for — and the precision that remains still reads as a plausible number. A signal
that spikes exactly once, `horizon` bars before each turn, pins the boundary
from both sides.

The reading rule also changed while the tests were being written. `lift > 1.0`
called two of this module's own control fixtures forecasts, at 1.07 and 1.16
over forty calls, on waves whose period no turn follows. The floor is a required
argument now and has to sit above one.
