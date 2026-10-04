---
id: REQ-WP-085
title: "The lower panes include volume, drawn from the bars the page already loads"
type: work-package
prd_ref: "§27.3; owner's direction 2026-10-04"
prd_lines: "4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-027, REQ-WP-083, REQ-WP-084]
tags: [web, chart, panes, volume]
hard_gated: false
---

## Requirement

PRD §27.3 lists the selectable lower panes, and the first one is **volume**:

- volume;
- CVD;
- OFI;
- OI;
- funding;
- basis;
- liquidations;
- DEX swap imbalance;
- DEX active liquidity.

The page has nine panes and volume is not among them. `apps/web/src/panes.ts` lists CVD, OFI (1m), **Depth
imbalance (10)**, Open interest, Funding (z), Basis (bps), Liquidations (5m), DEX swap imbalance and DEX active
liquidity: a pane §27.3 does not list stands where the one it does list should be, and the comment above the
list ("all nine are here") is wrong. On 2026-10-04 the owner looked at the pane row, saw buttons with nothing
behind them, and said the data "should already be there, especially volume".

For volume it is: **every bar carries `volume_base`** (the API's `BarOut`), and the chart page already loads the
bars. Volume needs no feature producer, no new feed and no new API field. This requirement adds the pane.

- **Volume is a pane**, the first in the row as §27.3 lists it, drawn per bar from the loaded bars and aligned
  with them in time. It is a property of the bars, not of the features table, so it reads the bars rather than
  a feature series.
- **It is as honest as the other panes.** Volume `0` is data (a bar in which nothing traded); a bar that is
  not final (`is_final` false) is not drawn as a finished bar's volume, the same rule the chart applies to
  candles. With no bars there is no volume, and the pane says "no data" under [[REQ-WP-084]]'s rule.
- **The page opens on it** when it has data: it is the first pane with data in the row, and a reader's valid
  choice is never overridden ([[REQ-WP-084]]).
- **The wrong claim is corrected.** The comment above the pane list stops saying all nine of §27.3 are present,
  and says which §27.3 panes exist, which do not yet have data, and that `depth_imbalance_10` is a pane this
  deployment added beyond the PRD's list. Whether to keep it is not decided here; it is not removed.

It changes nothing about the other panes' sources, about the API, or about how bars are loaded.

## Acceptance

- The pane row lists volume first, with the label "Volume"; the other panes keep their labels, order and
  behaviour.
- With loaded bars, the volume pane is a button and draws one value per final bar, equal to that bar's
  `volume_base`, at that bar's time; a bar with volume `0` is drawn at zero, not skipped.
- A bar that is not final contributes no volume point.
- With no bars, or a failed bars load, the volume pane is not offered as live: "no data" for none, the failure
  message for a failure ([[REQ-WP-084]]'s rule: a failure is not an absence).
- A volume is a decimal string on the wire and is parsed without losing the value the API sent for the range of
  real volumes (tested with a value that does not survive a naive conversion to a two-decimal figure).
- With volume present and no feature data, the page opens with volume selected; with feature data present
  too, a reader's earlier valid choice stays.
- The comment above the pane list is true: it names the §27.3 panes, which have data today (volume) and which
  have none yet, and the added `depth_imbalance_10`.
- **Looked at:** a screenshot of the chart with the volume pane drawn, light and dark, from the running build,
  kept under `docs/ui/`.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-134-volume-pane]]
- **Tests:**
    - `tests/unit/web/test_volume_pane_artifacts.py::test_every_module_this_requirement_touches_names_it[App.tsx]`
    - `tests/unit/web/test_volume_pane_artifacts.py::test_every_module_this_requirement_touches_names_it[FlowPane.tsx]`
    - `tests/unit/web/test_volume_pane_artifacts.py::test_every_module_this_requirement_touches_names_it[panes.ts]`
    - `tests/unit/web/test_volume_pane_artifacts.py::test_there_is_a_live_screenshot_of_the_volume_pane_in_each_scheme[dark]`
    - `tests/unit/web/test_volume_pane_artifacts.py::test_there_is_a_live_screenshot_of_the_volume_pane_in_each_scheme[light]`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/FlowPane.tsx`
    - `apps/web/src/__tests__/chartPanesLoading.test.tsx`
    - `apps/web/src/__tests__/chartVolumeOpens.test.tsx`
    - `apps/web/src/__tests__/flowPaneVolume.test.tsx`
    - `apps/web/src/__tests__/volumeAvailability.test.ts`
    - `apps/web/src/__tests__/volumePane.test.ts`
    - `apps/web/src/panes.ts`
- **Outcomes:** [[OUT-2026-10-04-implement-volume-pane]], [[OUT-2026-10-04-plan-volume-pane]], [[OUT-2026-10-04-spec-volume-pane]], [[OUT-2026-10-04-tasks-volume-pane]]
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 after the pane row showed buttons with no data behind them. The other
panes' data is real separate work: CVD can be computed from trades already ingested but nothing feeds the
feature code ([[REQ-WP-011]] built it); OFI and depth imbalance need a top-of-book subscription; OI, funding,
basis and liquidations need derivatives feeds; the DEX panes need DEX ingest. None of that is this requirement.
