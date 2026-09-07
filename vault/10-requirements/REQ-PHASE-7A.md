---
id: REQ-PHASE-7A
title: Adaptive position / stop management (shadow → paper)
type: phase
prd_ref: "Phase 7A — Adaptive position / stop management (shadow → paper)"
prd_lines: "6871-6903"
phase: 7A
status: draft
depends_on: ["REQ-PHASE-7"]
tags: []
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

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
