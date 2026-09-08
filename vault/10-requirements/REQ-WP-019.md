---
id: REQ-WP-019
title: Price extrema / turning points
type: work-package
prd_ref: "WP-019 Price extrema / turning points"
prd_lines: "7072-7099"
phase: null
status: planned
depends_on: []
tags: []
---

## Requirement

Implement in this order:

1. research-only symmetric `k`-neighborhood labels;
2. directional-change live baseline;
3. adaptive threshold interface;
4. causal local-polynomial slope/curvature;
5. optional Kalman filtered slope;
6. `ExtremumCandidate`, `TurningPointForecast`, `ConfirmedExtremum`, outcome models;
7. Kafka topics and storage adapters;
8. chart overlays and `AS-SEEN-THEN` semantics;
9. structural turning-point score;
10. point-in-time dataset targets for max/min/no-turn;
11. direct logistic/boosted baseline;
12. GMDH forward-path derivative experiment;
13. root-stability analysis;
14. Telegram alert integration behind a feature flag.

Done when:

- future-bar invariance test passes;
- confirmation legality test passes;
- replay parity passes;
- direct baseline metrics exist;
- derivative experiment can return `NO_EDGE` without blocking product completion.

## Acceptance

- future-bar invariance test passes;
- confirmation legality test passes;
- replay parity passes;
- direct baseline metrics exist;
- derivative experiment can return `NO_EDGE` without blocking product completion.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
