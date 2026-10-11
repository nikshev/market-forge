---
id: OUT-2026-10-11-spec-live-panes
step: spec
records: [REQ-WP-093, REQ-WP-094, REQ-WP-095, REQ-WP-096, REQ-WP-097]
commit: null
---

## What was done

The owner asked on 2026-10-11 why four lower panes read "no data" and then asked for every pane to show data.
Five requirements were written and specified together, one commit, because they share one architecture
([[ADR-070]]) and a spec read alone would repeat it:

- [[REQ-WP-093]] / spec 145 -- open interest, funding (z), basis, from a REST collector;
- [[REQ-WP-094]] / spec 146 -- liquidations, from each venue's stream;
- [[REQ-WP-095]] / spec 147 -- OFI, depth imbalance and the venue quotes, from a top-of-book subscription;
- [[REQ-WP-096]] / spec 148 -- the consensus rows the venue-basis pane reads;
- [[REQ-WP-097]] / spec 149 -- the acceptance of the whole, on the deployed stack.

The ask began as a question, answered by reading the code and the live API: the ingest subscribes to trades only,
the features and the maths exist, and **nothing produces any other input**. The worker writes six features and
does not iterate the registry. That finding, not a guess, is what the specs rest on.

## What was decided

- **A separate collector service writes raw tables; the worker is the only writer of features** (ADR-070). Two
  writers to one Iceberg table would conflict at commit; one writer keeps the point-in-time rule testable in
  one place.
- **Measured before specified.** Every endpoint and stream the specs name was probed from this host the same
  day. Two surprises changed the specs: the code comment that the futures websocket streams are unreachable is
  stale (they connect); and `funding_z` needs 24 settled rates *and* a fresh settlement, which with the
  library's 5-minute default would exist for five minutes in every eight hours -- so the staleness bound is
  per feature, and funding history is loaded once from each venue's public history.
- **Binance's open interest in USD is the venue's own figure** from the 5-minute history endpoint, because the
  base-unit endpoint would need a price of our choosing (`oi_series` skips such states deliberately).
- **A spot series is given its own venue's perpetual for derivatives**, stated and declared in one place.
- **Snapshot-style book streams, summarised per minute in event time**; the raw book is not archived.
- **Quiet is a reading only where the collector was listening** (liquidations): the collector's heartbeat is
  the proof, and the imbalance of an empty window is absent.
- **The venue-basis pane works for the two perpetual venues; Binance's spot panes say why not** (one spot venue,
  no consensus). A second spot venue is recorded as an option, not decided.
- **No `[NEEDS CLARIFICATION]` markers**: the choices that could have needed one had a reasonable default, and each
  is in the spec's Assumptions.

## What is still open

- **DEX panes** (swap imbalance, active liquidity): not covered. The pure code and tables exist but there is no
  RPC client, no ingest entrypoint, no compose service, and the DEX entity is a venue_symbol with no bars to
  hang a chart on. It is a different size of work and needs the owner's decision on the series.
- **OKX's top-of-book stream shape** (5 vs 10 levels) is for the plan; recorded in spec 147's Assumptions.
- **Bybit's liquidation side semantics** is for the plan to close with a recorded frame (spec 146).
- **The worker rebuild** deploys everything committed since 2026-10-08; it is held until the pass has been run
  against the real lakehouse without writing.
- **Host load** with five books and three collectors on a shared machine is unmeasured until the plan's
  measurement.
