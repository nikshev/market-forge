---
id: REQ-PHASE-7A
title: Adaptive position / stop management (shadow → paper)
type: phase
prd_ref: "Phase 7A — Adaptive position / stop management (shadow → paper)"
prd_lines: "6871-6903"
phase: 7A
status: planned
depends_on: ["REQ-PHASE-7"]
tags: []
covers: [REQ-WP-020, REQ-EXP-017, REQ-BIAS-009, REQ-BT-001]
not_delivered:
  - "stop-path chart: the web app has no stop-path view"
  - "Telegram stop-update notification: the alerting layer sends signals, not stop updates"
  - "shadow/paper replay of stop-update activation latency: the replay models fills, not activation latency"
---

## Requirement

Deliverables:

- `PositionState` and immutable position-event model;
- hard-stop vs adaptive-strategy-stop semantics;
- structural stop-anchor service;
- volatility/noise buffer;
- phase state machine (`INITIAL_RISK`, `PROTECTING`, `STRUCTURE_TRAIL`, `TREND_RIDE`, `DEFENSIVE_TRAIL`);
- monotonic risk-tightening rule;
- cooldown/hysteresis/anti-churn;
- order-flow confirmation/veto;
- channel and turning-point integration;
- derivatives/DeFi context hooks;
- shadow stop proposals;
- counterfactual stop-policy replay;
- stop-path chart;
- Telegram stop-update notification;
- premature-stop and stop-efficiency report.

Acceptance:

- default policy cannot widen accepted initial risk;
- confirmed swing cannot be used before `known_at`;
- appending future market data does not mutate historical stop proposals;
- naive trailing baseline vs adaptive policy report exists;
- stale-data freeze test passes;
- paper/shadow replay models stop-update activation latency;
- policy can return `NO_CHANGE` indefinitely when no better causal invalidation anchor exists.

Live exchange stop modification is **not** required for this phase.

## Acceptance

- default policy cannot widen accepted initial risk;
- confirmed swing cannot be used before `known_at`;
- appending future market data does not mutate historical stop proposals;
- naive trailing baseline vs adaptive policy report exists;
- stale-data freeze test passes;
- paper/shadow replay models stop-update activation latency;
- policy can return `NO_CHANGE` indefinitely when no better causal invalidation anchor exists.

Live exchange stop modification is **not** required for this phase.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-020]]
- [[REQ-EXP-017]]
- [[REQ-BIAS-009]]
- [[REQ-BT-001]]

**Not delivered:**

- stop-path chart: the web app has no stop-path view
- Telegram stop-update notification: the alerting layer sends signals, not stop updates
- shadow/paper replay of stop-update activation latency: the replay models fills, not activation latency

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_7a_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
