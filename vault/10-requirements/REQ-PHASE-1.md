---
id: REQ-PHASE-1
title: CEX channel MVP
type: phase
prd_ref: "Phase 1 — CEX channel MVP"
prd_lines: "6695-6719"
phase: 1
status: planned
depends_on: ["REQ-PHASE-0"]
tags: []
covers: [REQ-WP-003, REQ-WP-005, REQ-WP-006, REQ-WP-007, REQ-WP-008, REQ-WP-009, REQ-WP-010, REQ-US-001, REQ-US-002, REQ-US-003, REQ-NRT-A, REQ-NRT-E]
not_delivered:
  - "market metadata: instrument metadata beyond the symbol is not ingested"
---

## Requirement

Deliverables:

- Binance perp + spot connector;
- trades;
- bars;
- basic market metadata;
- rolling OLS residual-quantile channel;
- immutable channel snapshots;
- boundary/middle state machine;
- Telegram;
- React chart;
- deep-link;
- bar-replay backtest.

Acceptance:

- live BTC/ETH/SOL channels update;
- historical snapshots never mutate;
- signal opens exact chart state;
- future-leak test passes;
- at least one backtest report generated.

## Acceptance

- live BTC/ETH/SOL channels update;
- historical snapshots never mutate;
- signal opens exact chart state;
- future-leak test passes;
- at least one backtest report generated.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-003]]
- [[REQ-WP-005]]
- [[REQ-WP-006]]
- [[REQ-WP-007]]
- [[REQ-WP-008]]
- [[REQ-WP-009]]
- [[REQ-WP-010]]
- [[REQ-US-001]]
- [[REQ-US-002]]
- [[REQ-US-003]]
- [[REQ-NRT-A]]
- [[REQ-NRT-E]]

**Not delivered:**

- market metadata: instrument metadata beyond the symbol is not ingested

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_1_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
