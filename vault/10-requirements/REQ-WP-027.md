---
id: REQ-WP-027
title: The chart has selectable lower panes for order-flow features
type: work-package
prd_ref: "§27.3, §45 Phase 2"
prd_lines: "4423-4435, 6751"
phase: 2
status: draft
depends_on: [REQ-WP-009, REQ-WP-011, REQ-API-001]
tags: [frontend]
---

## Requirement

PRD §27.3, in full:

    ## 27.3. Lower panes

    Selectable panes:

    - volume;
    - CVD;
    - OFI;
    - OI;
    - funding;
    - basis;
    - liquidations;
    - DEX swap imbalance;
    - DEX active liquidity.

PRD §45's Phase 2 lists "UI panes" among its deliverables, and it is the only
entry in [[REQ-PHASE-2]]'s `not_delivered`: the web app draws candles, channels,
zones, a marker and a volume profile, and has no lower pane at all.

**Scope is Phase 2's own subject: the order-flow and order-book features.** Of
§27.3's nine panes, CVD, OFI and depth imbalance are the ones Phase 2 delivers
data for — [[REQ-WP-011]] registers `cvd`, `cvd_slope`, `ofi_1s` through
`ofi_1m`, `ofi_bar` and `depth_imbalance_*`, and `GET /api/v1/features/timeseries`
already serves them. The derivatives panes (OI, funding, basis, liquidations)
belong to Phase 3's own deliverable and the DEX panes to Phase 4; building them
here would deliver panes for data those phases have not finished.

## Acceptance

- a reader can select which pane is shown, from the ones this phase's data
  supports;
- a pane draws the feature it names and nothing else;
- **a point that carries no value for the selected feature leaves a gap, never
  a zero** — a market with no order-flow reading and one with a reading of zero
  are different facts, and a flat line at zero reads as the second;
- a series with no points at all says so, rather than rendering an empty pane
  that could be mistaken for a quiet market;
- a failed load says so and is distinguishable from an empty one;
- what the chart already draws is unchanged.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

**The decision about what to draw is separated from the drawing**, because that
is what this application already does and for a reason it writes down:
`lightweight-charts` needs a laid-out container and jsdom does not provide one,
so a component test can never see a line. The part that can be wrong — which
points, which gaps, which refusal — goes in a module that is tested; the
component attaches it.

**The gap rule is the requirement's spine.** A feature is a key in a mapping per
instant, and a mapping without that key is silent rather than zero. The same
distinction three other requirements in this repository have had to make, and
this is the first place it would be drawn on a screen and believed.

Extracted by hand: §27.3 is a list of panes with no acceptance criteria of its
own, so the criteria above are **derived** — from §27.3's list, from Phase 2's
scope, and from this application's existing rules about empty and failed loads
([[REQ-WP-009]]'s FR-016).
