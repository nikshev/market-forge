---
id: REQ-WP-020
title: Adaptive stop management
type: work-package
prd_ref: "WP-020 Adaptive stop management"
prd_lines: "7100-7136"
phase: null
status: draft
depends_on: ["REQ-WP-006", "REQ-WP-011", "REQ-WP-013", "REQ-WP-019"]
tags: []
---

## Requirement

Implement in this order:

1. `PositionState`, `StopAnchor`, `StopProposal`, `StopPolicyOutcome` models;
2. manual/shadow position ingestion;
3. initial structural stop + causal volatility/noise buffer;
4. deterministic position-phase state machine;
5. confirmed-swing trailing baseline;
6. monotonic tightening guard;
7. minimum-distance guard;
8. hysteresis/cooldown/anti-churn;
9. channel-aware anchors;
10. order-flow confirmation/veto;
11. turning-point transition into defensive mode;
12. derivatives/DeFi context adapters;
13. data-quality freeze;
14. counterfactual stop-policy replay;
15. naive fixed-percent and ATR trailing baselines;
16. UI stop path + reason inspector;
17. Telegram stop-update event;
18. optional exchange reconciliation interface behind disabled feature flag.

Done when:

- no-future-swing legality test passes;
- LONG/SHORT monotonic tightening tests pass;
- stop-path replay is deterministic;
- adaptive vs naive OOS report exists;
- premature-stop metric exists;
- stop update latency is represented in replay;
- module is usable in shadow/paper mode without any exchange trading key;
- ML is not required for baseline completion.


---

## Acceptance

- no-future-swing legality test passes;
- LONG/SHORT monotonic tightening tests pass;
- stop-path replay is deterministic;
- adaptive vs naive OOS report exists;
- premature-stop metric exists;
- stop update latency is represented in replay;
- module is usable in shadow/paper mode without any exchange trading key;
- ML is not required for baseline completion.


---

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
