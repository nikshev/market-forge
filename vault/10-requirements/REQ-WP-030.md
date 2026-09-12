---
id: REQ-WP-030
title: The chart has lower panes for the derivatives features
type: work-package
prd_ref: "§27.3, §45 Phase 3"
prd_lines: "4423-4435, 6768"
phase: 3
status: implemented
depends_on: [REQ-WP-027, REQ-WP-013, REQ-API-001]
tags: [frontend]
---

## Requirement

PRD §27.3's selectable panes list nine. [[REQ-WP-027]] built three — CVD, OFI
and depth imbalance — and named the rest as other phases' work in so many words:

> OI, funding, basis and liquidations are Phase 3's own deliverable and the DEX
> pair is Phase 4's. Offering an empty pane and calling it a feature would put a
> phase's unfinished work in front of a reader as though it were finished.

Phase 3's data is finished. [[REQ-WP-013]] registers `open_interest_usd`,
`oi_change_5m`, `funding_z`, `basis_bps` and `liquidation_imbalance_5m`, and
`GET /api/v1/features/timeseries` serves any registered feature. Four of §27.3's
remaining panes therefore have data behind them, and [[REQ-PHASE-3]]'s
`not_delivered` still names "derivatives feature panel: the web app has no
derivatives pane".

**What this is not.** It is not a new mechanism. The pane machinery, the gap
rule, the three empty-ish states and their tests all exist; this is the second
caller of a road [[REQ-WP-027]] paved, and the interesting question is whether
that road carries a second load without changing.

## Acceptance

- panes for open interest, funding, basis and liquidations are offered beside
  the order-flow ones;
- every offered pane names a feature the registry knows, checked mechanically
  rather than by eye;
- a derivatives pane obeys the rules the order-flow panes obey: a missing value
  is a gap, a recorded zero is drawn, and the three empty-ish states stay apart;
- the DEX panes are still absent, because Phase 4's data is;
- nothing the existing panes do changes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-068-derivatives-panes]]
- **Tests:**
    - `tests/unit/features/test_pane_features.py::test_a_pane_list_it_cannot_read_is_a_failure_not_an_empty_answer`
    - `tests/unit/features/test_pane_features.py::test_every_offered_pane_names_a_registered_feature`
    - `tests/unit/features/test_pane_features.py::test_the_derivatives_panes_are_offered`
    - `tests/unit/features/test_pane_features.py::test_the_order_flow_panes_are_still_offered`
- **Code:**
    - `apps/web/src/panes.ts`
- **Outcomes:** [[OUT-2026-09-10-implement-derivatives-panes]], [[OUT-2026-09-10-plan-derivatives-panes]], [[OUT-2026-09-10-requirement-derivatives-panes]], [[OUT-2026-09-10-spec-derivatives-panes]]
<!-- trace:end -->

## Notes

**The mechanical check is the point of this requirement, not the four entries.**
Adding a pane is a line in a list; the failure it invites is a pane naming a
feature nobody registers, which renders as "no readings of this feature" forever
and looks like a quiet market rather than a typo. A test that compares the pane
list against the registry catches that at the moment it is written, and it is
what makes the fifth pane safe to add.
