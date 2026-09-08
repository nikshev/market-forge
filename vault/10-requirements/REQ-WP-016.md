---
id: REQ-WP-016
title: Cross-venue
type: work-package
prd_ref: "WP-016 Cross-venue"
prd_lines: "7049-7054"
phase: null
status: draft
depends_on: ["REQ-ASSET-001", "REQ-WP-004", "REQ-WP-015"]
tags: []
---

## Requirement

- canonical instrument mapping;
- consensus price;
- basis.

## Acceptance

Consensus price (§17.1):

- a consensus mid is the median of normalized mids across the selected venues,
  and the result names the venues that contributed;
- a venue whose mid is missing, or older than a configurable staleness
  tolerance at the instant asked about, does not contribute, and the
  contributor count is reported;
- a consensus over fewer than two contributing venues is refused.

Basis (§17.3, §18.14):

- `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)` is computed for
  each contributing venue;
- mid-based basis is refused when either side is an AMM, and
  `executable_basis_bps(N)` is computed instead, from executable prices at a
  notional supplied by the caller.

Lead-lag (§17.2):

- per-venue returns over 1/5/10 s windows and pairwise lagged correlations are
  computed from data available at the instant asked about;
- lead-lag outputs are marked research-only, and no signal-path module imports
  them, asserted over the source.

Fragmentation and liquidity (§17.4):

- depth by venue at 10/25/50 bps is reported, each venue measured by its own
  executable-depth measure;
- the best effective execution venue for a fixed notional is identified from
  all-in cost, not from top-of-book price;
- liquidity concentration across venues is reported.

Throughout:

- every output is computed from data available at the instant asked about; no
  venue's later value is used.

## Trace

<!-- trace:begin -->
- **Outcomes:** [[OUT-2026-09-08-requirement-cross-venue-acceptance]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-08. PRD §17 describes the engine in four subsections and states no
acceptance criteria of its own; the criteria were derived from those subsections
and approved by the repository owner. The derivation, the alternatives
considered and the reasoning for each criterion are in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`.

Two points that document settles and this note should not restate in full:

- **"Canonical instrument mapping" is not defined in §17.** It is §18.13's asset
  registry, extracted as `REQ-ASSET-001`, which this requirement now depends on.
- **§17.3's mid-based basis and §18.14's executable basis are both required,
  under different names.** §18.14 forbids comparing a CEX top-of-book quote
  against an AMM spot quote, so the mid-based figure is refused for any pair
  involving an AMM rather than computed with a caption.

Scope deliberately excludes a second CEX connector: no work package in the PRD
builds one, and Bybit and OKX are named in §17.2 without appearing in the
work-package list. Binance and Uniswap v3 are two venues, and enough to exercise
every criterion.
