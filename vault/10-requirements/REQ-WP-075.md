---
id: REQ-WP-075
title: The markets route shows current state and opens a chart from it
type: work-package
prd_ref: "§27.1, §28.1"
prd_lines: "4390-4405, 4463-4474"
phase: null
status: draft
depends_on: [REQ-US-001, REQ-WP-074]
tags: []
---

## Requirement

§27.1 lists the routes, verbatim:

> ```text
> /markets
> /chart/:venue/:symbol
> /signals
> /signals/:signalId
> /research/backtests/:runId
> ```

`/markets` is the overview. §28.1 gives it a read — `GET /api/v1/markets`, with
filters `venue`, `market_type`, `quote`, `active`, `min_volume` — and that
endpoint is already built and ordered by §43's rank score.

What does not exist is the view. The application renders every path that is not
`/chart/:venue/:symbol` as the same two lines, "ChannelFlow" and "Open a chart at
/chart/&lt;venue&gt;/&lt;symbol&gt;", because `parseDeepLink` returns `null` and
`App` has no other branch.

**The PRD names no `/` route.** Serving `/markets` at the root as well is this
deployment's decision, recorded here rather than left as an undocumented
redirect: a reader comparing §27.1 with the running app should find the
difference explained, not have to infer it.

### What "current state" is allowed to mean

The list is the state: one row per market, carrying what §28.1's read already
returns and what §43 already scores. This requirement does **not** introduce a
new aggregate, a new endpoint, or a number nobody computes today — a dashboard
that invents its own figures is a second source of truth for the same
quantities.

An unscored market must read as unscored. The API's own rule is that ranking it
at zero "would place it among the worst setups, saying it had been examined and
found weak"; a view that renders a null as `0.00` undoes that at the last step.

## Acceptance

- `/markets` renders one row per market from `GET /api/v1/markets`, in the order
  the API returned them. The view does not re-sort: the order is §43's rank, and
  a client-side sort would silently replace it.
- A market the API reports as unscored is shown as unscored — not as zero, not as
  an empty cell that reads like a low value.
- The root path renders this view, not the placeholder.
- Choosing a market and a timeframe navigates to §27.1's deep link,
  `/chart/:venue/:symbol?tf=<timeframe>`, so a selection and a pasted link
  produce the same page. Proven by comparing the two.
- The timeframes offered are the configured set ([[REQ-WP-073]]), obtained rather
  than written into the frontend as a second list that can disagree with the
  first.
- A failed load is stated, in the manner FR-016 already requires of the chart —
  never rendered as an empty list, which reads as "no markets".

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
