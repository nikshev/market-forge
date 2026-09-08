---
id: OUT-2026-09-08-requirement-cross-venue-acceptance
step: spec
records: [REQ-WP-016, REQ-ASSET-001]
commit: null
---

## What was done

`REQ-WP-016`'s `ACCEPTANCE-NOT-SPECIFIED` marker replaced with eleven criteria
derived from PRD §17, and `REQ-ASSET-001` extracted from §18.13 as the registry
they depend on. The derivation is in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`.

Nine notes still carry the marker, down from ten. `CLAUDE.md`'s count corrected.

## What was decided

- **Scope is all four §17 subsections**, not the three the work package's body
  names. Four merged work packages had already deferred specific things here —
  funding and basis dispersion (`REQ-WP-013`), book consolidation
  (`REQ-WP-004`), §44A.15's context (`REQ-WP-020`) — and leaving lead-lag and
  fragmentation out would have left those deferrals pointing at nothing.
- **Both kinds of basis, separately named.** §17.3 defines basis over mids;
  §18.14 forbids exactly that comparison when one side is an AMM. The mid-based
  figure is refused for AMM pairs rather than computed with a caption, because a
  caption does not travel with a number. Both halves of the executable
  comparison already exist: `depth_within_bps` and `depth_to_bps`.
- **§18.13 becomes its own requirement.** It answers "is this the same asset";
  §17 answers "how do these venues relate". No work package names §18.13 —
  `REQ-WP-014`'s acceptance is logs, finality, reorgs, ABI and RPC health;
  `REQ-WP-015`'s is pool math, decoding, tick state and depth. Same precedent as
  `REQ-API-001` for §28, and the cost of not splitting is visible already in
  `REQ-WP-019`, which sits at `tested` because two of its criteria need
  subsystems that were not built with it.
- **§17.2's prohibition made checkable.** "Do not convert correlation to trading
  rule without OOS validation" cannot be verified as written; that no
  signal-path module imports the lead-lag module can. Third use of a shape that
  worked twice already — [[ADR-022]]'s transform declaration and [[ADR-027]]'s
  inert regime label.

## What these criteria deliberately do not require

- **A second CEX connector.** No work package in the PRD builds one; Bybit and
  OKX are named in §17.2 and appear nowhere in the work-package list. Binance
  and Uniswap v3 are two venues and exercise every criterion.
- **§17.1's volume/depth weighted median**, which the PRD marks experimental.
- **Any trading rule derived from lead-lag**, until `REQ-WP-017` and
  `REQ-WP-018` supply the OOS validation §17.2 requires.

## What is still open

- Both requirements are at `draft` and unimplemented. Nothing was built here;
  this step produced the criteria that let them enter the pipeline.
- **`REQ-ASSET-001` must land before `REQ-WP-016`**, which now declares the
  dependency.
