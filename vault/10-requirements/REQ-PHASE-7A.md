---
id: REQ-PHASE-7A
title: Adaptive position / stop management (shadow → paper)
type: phase
prd_ref: "Phase 7A — Adaptive position / stop management (shadow → paper)"
prd_lines: "6871-6903"
phase: 7A
status: implemented
depends_on: ["REQ-PHASE-7"]
tags: []
covers: [REQ-WP-020, REQ-EXP-017, REQ-BIAS-009, REQ-BT-001, REQ-WP-032, REQ-WP-033, REQ-WP-034]
not_delivered: []
blocked: []
deferred: []
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

Closed 2026-09-10 by [[REQ-WP-034]]. The phase's fifteen deliverables reduce to
one claim — a stop may tighten risk and may never widen it — and three ways of
keeping that claim honest:

- **the engine** ([[REQ-WP-020]]): the state machine, the anchors, the buffer,
  the monotonic rule, and [[ADR-032]]'s insistence that a hold is a proposal, so
  six different reasons for not moving stay six different facts;
- **the evaluation** ([[REQ-BT-001]], [[REQ-BIAS-009]], [[REQ-EXP-017]],
  [[REQ-WP-033]]): a counterfactual replay against a naive baseline, net of
  costs, in which a decided stop is not an obeyed stop — §44A.27's own example
  now runs as a test;
- **what a person sees** ([[REQ-WP-032]], [[REQ-WP-034]]): a path shown as it
  was generated rather than recomputed, and a notification that reports the
  transition rather than the state.

Every acceptance line holds. The two that took the most work were the two about
things not being where they appear to be: a confirmed swing cannot be used
before `known_at`, and a stop update is not effective until it is acknowledged.

What the phase does not do, and never claimed to: live exchange stop
modification is explicitly out of scope above, and nothing constructs a
dispatcher or serves a position outside its own package — the same waiting state
the signal alert has been in since Phase 2, on a live mode §25.1 does not yet
describe.
