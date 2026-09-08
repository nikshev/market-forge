---
description: "Task list for REQ-WP-015"
---

# Tasks: Uniswap v3 adapter

- [x] T001 Write failing `test_math.py`: the three price representations, round trips at the tick extremes, flooring, decimals, refusals (SC-001).
- [x] T002 Implement `math.py` (FR-001 to FR-004).
- [x] T003 Write failing `test_pool.py`: canonical ordering against arrival order; the transaction-index tie-break; duplicate refusal; mint/burn symmetry; active liquidity only for spanning ranges; `Collect` inert; the integrity check (SC-002 to SC-005, SC-009).
- [x] T004 Implement `events.py` and `pool.py` (FR-005 to FR-011, FR-015).
- [x] T005 Write failing `test_depth.py`: single-range depth against the closed form; crossing changes liquidity; unreachable targets; both directions; the asymmetry report (SC-006 to SC-008).
- [x] T006 Implement `depth.py` (FR-012 to FR-014).
- [x] T007 Mutation-check seven guards, verifying every restore.
- [x] T008 Assert no module consults a clock or opens a socket (FR-016, SC-010).
- [x] T009 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-004 | T002 |
| FR-005 to FR-011, FR-015 | T004 |
| FR-012 to FR-014 | T006 |
| FR-016 | T008 |
| SC-001 | T001 |
| SC-002 to SC-005, SC-009 | T003 |
| SC-006 to SC-008 | T005 |
| SC-010 | T008 |

## Notes

T007's first mutation is PRD §18.7's named trap: sorting by block alone, which
is what a timestamp sort degenerates to. It applies a swap before the mint that
supplied its liquidity, and the resulting pool is plausible in every field.
