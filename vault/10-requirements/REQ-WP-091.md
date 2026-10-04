---
id: REQ-WP-091
title: "The chart can show the cross-venue consensus mid and the viewed venue's basis to it"
type: work-package
prd_ref: "§17.1, §17.3, §17.2, §44A.15; owner's direction 2026-10-04"
prd_lines: "2520-2552, 5910-5925"
phase: null
status: draft
depends_on: [REQ-WP-016, REQ-WP-083]
tags: [web, chart, cross-venue, consensus, basis]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner looked at an ETHUSDT chart titled "binance" and asked whether the plan had not been to
show something averaged over all sources, DeFi included, and what the PRD says. It says:

- §17.1 **Consensus price**: "Create robust consensus mid from selected high-liquidity venues." Method: the
  median of normalized mids; a volume- or depth-weighted median is experimental.
- §17.3 **Cross-venue basis**: `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)`.
- §17.2 lead-lag features include the DEX's marginal return as one more series; §44A.15 treats DeFi as
  *context* (DEX-CEX executable basis, depth asymmetry, swap imbalance), not as part of a price.
- The chart and the API are per venue: `/chart/:venue/:symbol` (§27.1) and `GET /bars` with `venue` and
  `symbol` (§28.2). The PRD defines no consolidated bar series and does not say the chart draws the consensus.

What exists, read from the code on 2026-10-04: `crossvenue/` ([[REQ-WP-016]], implemented) has
`consensus_mid(quotes, registry, at_ns, staleness_ns)` (the median over the fresh quotes of at least two venues
for one asset; a quote later than the instant or too old is excluded with a stated reason; one venue is refused,
since "a median over one venue is that venue's mid wearing a better name"), `basis_bps`, an executable basis and
a fragmentation table. **Nothing outside the library calls it**: no API route, no pipeline pass, no page. And
it needs **mids**, i.e. top-of-book quotes, while the ingest reads trades only, so no venue's mid is available at all.

This requirement makes the consensus visible, in two steps that can ship separately:

1. **The consensus mid line.** The chart can draw the consensus mid over its candles (an optional layer, off by
   default), computed as of each bar's close from the fresh mids of the venues that have one; where fewer than two
   venues contribute, the line is absent there and the chart says why, never a one-venue "consensus".
2. **The venue's basis.** `basis_bps` of the viewed venue to the consensus, as a lower pane (§27.3 lists "basis").

Rules that hold: **no look-ahead** (the consensus at `t` uses only quotes observed at or before `t`, as
`consensus_mid` already enforces); **one asset** (the registry decides which venues are the same underlying, as the
library does); and the **name** `basis_bps` is already taken by [[REQ-WP-030]]'s *derivatives* basis (perp price
against spot price, `derivatives/openinterest.py`), which is a different quantity. The cross-venue one needs its own
feature name (for example `venue_basis_bps`) so the registry and the pane list never confuse the two.

**Not in this requirement**: DeFi in the consensus (§17.1 names "selected high-liquidity venues"; the DEX enters
lead-lag and executable basis, which need DEX ingest, not running in the compose stack), a consolidated bar series,
and the book subscription itself (below).

## Acceptance

- For fixtures of quotes from two and three venues of one asset, the consensus equals the median of the fresh mids; a
  stale quote and a quote later than the instant are excluded with a reason; one venue gives no consensus.
- A consensus at bar time `t` is unchanged when quotes later than `t` are appended (a test).
- The chart draws the consensus line when the layer is on and no line, with the reason, where fewer than two venues
  contribute; with the layer off it draws nothing extra.
- The venue basis pane draws `10000 * (mid_i / consensus_mid - 1)` for the viewed venue, with a feature name that
  does not collide with `basis_bps`, registered with its `FeatureSpec`.
- Mixed instrument types (the Binance spot symbol with Bybit and OKX perpetuals) are handled by a stated rule, not by
  accident: the spec decides whether consensus is taken per market type or normalised across them, and a test pins it.
- On the running stack, after the book data exists, a screenshot of a chart with the consensus line and the basis
  pane, light and dark, is kept under `docs/ui/` and looked at.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

This depends on **top-of-book mids from at least two venues**, which the ingest does not read: a quote stream
(Binance `bookTicker`, Bybit and OKX tickers) is a separate piece of work with its own requirement and is the
same subscription [[REQ-WP-011]]'s OFI and depth-imbalance panes are waiting for. The ordering that follows from it:
book subscription first, then this, with the OFI and depth features arriving from the same data.

Mixed spot and perpetual instruments are the open design question. A median over a spot mid and two perpetual mids
blends the spot-perp basis into the "consensus"; §17.1's "normalized mids" does not say how. Taking the consensus
within a market type avoids it but leaves one venue per type today (Binance spot; Bybit and OKX perps).
