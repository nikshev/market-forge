---
id: REQ-WP-084
title: "The chart hides candidate extrema until asked, and a lower pane with no data says so instead of offering a dead button"
type: work-package
prd_ref: "§27.2, §27.3; owner's direction 2026-10-04 (after Material UI)"
prd_lines: "4406-4436"
phase: null
status: draft
depends_on: [REQ-WP-083, REQ-WP-027, REQ-WP-009]
tags: [web, chart, panes, extrema]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner looked at the chart and asked two things: what the small arrows are, and why the
buttons under the chart do nothing. Both have an honest answer and neither is a good one.

- **The arrows** are the extrema detector's output. A filled glyph is a confirmed extremum; a grey, hollow "?"
  is a *candidate*, which the detector may still invalidate. There are many candidates, they sit on top of
  the price, and a reader with no knowledge of the detector sees noise. §27.2 asks for layers that can be
  toggled; candidates should be one, **off by default**, so that the first view of a chart shows the
  confirmed structure and the reader chooses to see the unconfirmed one. Confirmed extrema stay as they are.
- **The buttons** are §27.3's selectable lower panes (volume, CVD, OFI, OI, funding, basis, liquidations, DEX
  swap imbalance, DEX active liquidity). Today every pane is a button, and a pane whose feature has no
  stored series answers a press with an empty pane and a note. A button that can only ever produce "nothing"
  reads as broken. A pane that has no data is shown as such **before** it is pressed: "no data" in place of a
  live control, so the control row tells the reader what exists.

This requirement is about what the chart *shows and offers*. It does not produce the missing data: the
features table has no producer for CVD and OFI (computable from trades already stored), nor for the rest;
that is separate work. Until it lands, most panes will honestly read "no data", which is the point.

It changes nothing about which API calls are made for a pane that has data, nothing about what a candidate or
a confirmation *is*, and nothing a test finds by role or name for a pane that has data.

## Acceptance

- A chart opened with no layer choice in the link draws confirmed extrema and **no** candidates. A control
  named for candidate extrema turns them on and off; its state is visible (pressed), and turning it on draws
  the candidates the API returned, unchanged.
- A deep link that says candidates were on (or off) restores that, and a link that says nothing gets the
  default off. A link naming a layer the page does not know is still handled as [[REQ-US-002]] decided:
  discarded whole, with the notice.
- For a pane whose feature has no stored data for the market and timeframe, the control row shows "no data"
  for it instead of an active button; pressing is not possible, and assistive technology is told it is
  unavailable (not merely styled grey). A pane that has data is a button exactly as today.
- A pane that has data and later loses it (an empty response after a non-empty one) is shown as "no data",
  not as a live button with an empty chart. A failed load is still a failure, never "no data"
  ([[REQ-WP-009]] FR-016).
- Which panes have data is decided from what the API reports, not from a list in the page: a feature
  producer added later makes its pane live with no change to the page.
- **Looked at:** screenshots of the chart with the candidates off (default) and on, and of the pane row with
  some panes "no data", light and dark, are taken from the running build and kept under `docs/ui/`.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 after reading the Material UI screenshots; the follow-ups were agreed as
"after MUI". The mechanism for "which panes have data" is the spec's to settle (the features snapshot of
§28.4 is the likely source). The candidate toggle must not change the meaning of the deep link's `overlays`
list silently: adding a layer name to it is a decision for the spec, because an older link would otherwise
read as unreadable.
