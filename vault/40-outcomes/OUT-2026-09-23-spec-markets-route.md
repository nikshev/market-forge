---
id: OUT-2026-09-23-spec-markets-route
step: spec
records: [REQ-WP-075]
commit: null
---

## What was done

[[REQ-WP-075]] specified as `specs/120-markets-route/spec.md`, `traces:
[REQ-WP-075]`; note visible as [[SPEC-120-markets-route]].

## What was decided

**The view invents nothing.** "Current state" means §28.1's rows and §43's
order, presented. No new aggregate, no summarised percentage, no number that
does not already exist — a view with its own arithmetic would be a second
source of truth for quantities the API publishes, and the two would drift.

**No client-side re-sorting.** The API already orders by rank and places
unscored markets last with nulls ([[REQ-US-001]]). A sort in the view would
silently replace that order the day the API's ranking changes, which is the
same defect class as a second timeframe list.

**An unscored market reads as unscored.** The API is explicit that a zero for
an unscored market "would place it among the worst setups, saying it had been
examined and found weak". Rendering `null` as `0.00` would undo that rule in
the last step of the pipeline.

**The root path renders this view.** The PRD names no `/` route; leaving a
placeholder there is the product looking unfinished to every reader who arrives
without a path. The decision is recorded in the spec rather than left as an
undocumented redirect — and every other unknown path keeps the placeholder, so
a mistyped URL still says so.

**One timeframe per visit, chosen with the control the chart already has.**
Each row is a single link whose destination carries the selected timeframe.
Alternatives rejected: a per-row timeframe menu (six rows × eight timeframes of
controls for one decision), and no timeframe at all (the chart would open at
the default, making the choice implicit).

**The offered set is read, not written down.** FR-005 reuses
`GET /api/v1/timeframes`. With [[REQ-WP-074]] having settled that surface,
this view costs no new endpoint and cannot disagree about the set.

**Navigation is a link, not a router.** Two routes do not justify a routing
dependency; the chart already parses its link at mount.

**Filters are out of scope.** §28.1 supports five filters; the requirement asks
for the list. A filter UI is a separate decision, and smuggling one in would
have enlarged the acceptance without a requirement behind it.

## What is still open

- **What a market row shows beyond symbol, venue and scores** — a price, a
  sparkline, a 24-hour change — is not settled. The reference shape
  ([[REQ-WP-074]]'s investing.com toolbar) suggests a price, but no requirement
  or read produces one at market-list scale, and inventing it is exactly what
  this spec refuses.
- **The filters.** A later requirement can surface §28.1's parameters; the spec
  names their absence rather than pretending the omission is a decision about
  them.
- **`/signals` and `/research/backtests/:runId` remain placeholders.** §27.1
  lists five routes; this feature builds the second.
