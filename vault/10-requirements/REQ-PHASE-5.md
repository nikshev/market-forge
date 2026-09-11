---
id: REQ-PHASE-5
title: Cross-venue
type: phase
prd_ref: "Phase 5 — Cross-venue"
prd_lines: "6821-6832"
phase: 5
status: planned
depends_on: ["REQ-PHASE-4"]
tags: []
covers: [REQ-WP-016, REQ-ASSET-001, REQ-EXP-010, REQ-EXP-015, REQ-WP-043, REQ-WP-044]
not_delivered:
  - "Bybit connector: public market data lands ([[REQ-WP-043]]); the session layer and derivatives channels do not"
  - "OKX connector: public market data lands ([[REQ-WP-044]]); the session layer and derivatives channels do not"
  - "funding dispersion: no cross-venue funding series exists to disperse"
---

## Requirement

Deliverables:

- Bybit;
- OKX;
- normalized symbol mapping;
- consensus mid;
- cross-venue basis;
- depth comparison;
- funding dispersion.

## Acceptance

- each venue connector implements the shared canonical interface and passes the connector contract tests (§35.6, PRD §0 item 10);
- a symbol that cannot be resolved to a canonical instrument is refused rather than dropped or guessed;
- the consensus mid is the median of normalized mids across the venues that reported at the same instant, and a venue that did not report is excluded rather than carried forward (§17.1, §32);
- cross-venue basis is exactly `10000 * (mid_i / consensus_mid - 1)` (§17.3);
- depth is reported per venue at the 10/25/50 bps bands and the best effective execution venue is named for a fixed notional (§17.4);
- funding dispersion is reported across venues, and a venue whose funding is stale is excluded rather than reused (Phase 3's own criterion);
- no cross-venue correlation is converted into a trading rule without out-of-sample validation (§17.2).

_Derived, not quoted: the PRD states no acceptance criteria for this phase. Each line names the section it comes from; the derivation is recorded in `docs/superpowers/specs/2026-09-09-phase-acceptance-design.md`._

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-016]]
- [[REQ-ASSET-001]]
- [[REQ-EXP-010]]
- [[REQ-EXP-015]]

**Not delivered:**

- Bybit connector: only Binance is implemented
- OKX connector: only Binance is implemented
- funding dispersion: no cross-venue funding series exists to disperse

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_5_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
