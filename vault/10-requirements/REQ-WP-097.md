---
id: REQ-WP-097
title: "Every lower pane the running deployment can fill has data, and the ones it cannot say why"
type: work-package
prd_ref: "§27.3, §45 Phase 2, §45 Phase 3; owner's direction 2026-10-11"
prd_lines: "4423-4436, 6751, 6768"
phase: null
status: planned
depends_on: [REQ-WP-093, REQ-WP-094, REQ-WP-095, REQ-WP-096, REQ-WP-084]
tags: [panes, acceptance, deployment]
hard_gated: false
---

## Requirement

The owner's ask of 2026-10-11 was "make all the data display". Four requirements build the producers
([[REQ-WP-093]], [[REQ-WP-094]], [[REQ-WP-095]], [[REQ-WP-096]]); this one is the acceptance of the whole, on the
**deployed** stack, so that "every pane has data" is a recorded measurement and not a belief.

For every market the deployment lists and every timeframe the page offers, each of the ten lower panes (volume
and CVD from the bars, and the nine feature panes of §27.3 plus the depth-imbalance extra) is in exactly one of
three states, and the state is checked against the API:

- **has data**: at least one point in the loaded range;
- **absent for a stated reason that is true**: a spot market has no perpetual consensus; a symbol with no
  liquidation in the range; a DEX pane on a series with no DEX source;
- **never** "absent because the producer is not deployed" -- that is the state this requirement removes.

## Acceptance

- A recorded run (a script kept in `tools/`, its output in the outcome note) queries `/api/v1/features/timeseries`
  and the venue-basis read for every listed market and timeframe and prints the three-state table above. Any cell
  whose reason is "no producer" fails the run.
- The running containers are the ones the commits describe: the collector services are up, healthy, and have been
  for a measured interval; the worker's image was built from a clean committed tree.
- A screenshot of a chart with the pane row enabled is kept under `docs/ui/` and looked at, light and dark
  ([[REQ-WP-091]]'s own acceptance asks the same).
- DEX panes are listed by name with their state; if they are not built (a further requirement, if the owner asks for
  it) the table says "no DEX source" for them, which is a true reason and not a hidden one.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-149-pane-coverage]]
- **Outcomes:** [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

This is deliberately a requirement about the deployment. A green unit suite proved the six trade features and
said nothing about the nine panes that were empty for a month.
