---
id: REQ-EXP-017
title: Adaptive stop-management policy
type: experiment
prd_ref: "EXP-017 Adaptive stop-management policy"
prd_lines: "5252-5292"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Compare position-management policies on the exact same immutable entry signals:

1. fixed initial stop only;
2. naive fixed-percent trailing stop;
3. ATR/volatility trailing stop;
4. confirmed-swing structural trailing stop;
5. channel-conditioned structural stop;
6. structural stop + order-flow confirmation;
7. full Adaptive Stop Management Engine.

Primary metrics:

- expectancy after fees/slippage;
- realized R multiple;
- profit factor;
- stop-out rate;
- percentage of trades stopped before later reaching original target;
- give-back from MFE to realized exit;
- MAE before stop;
- median/95p stop distance;
- average holding time;
- turnover / stop modification count;
- tail loss / worst gap or slippage event;
- regime stability.

Ablations:

- remove swing confirmation;
- remove volatility/noise floor;
- remove order-flow veto;
- remove channel context;
- remove extremum/turning-point forecast;
- remove DeFi/cross-venue context;
- remove hysteresis/cooldown.

The experiment must be able to conclude `NO_EDGE`: a sophisticated trailing policy is rejected if it only looks better visually but does not improve OOS economics or risk-adjusted outcomes.

## Acceptance

- the seven policies (fixed initial stop; naive fixed-percent trailing; ATR/volatility trailing; confirmed-swing structural trailing; channel-conditioned structural stop; structural stop + order-flow confirmation; full Adaptive Stop Management Engine) are compared on identical immutable entry signals;
- primary metrics are reported: expectancy after fees/slippage, realized R multiple, profit factor, stop-out rate, percentage of trades stopped before later reaching original target, give-back from MFE to realized exit, MAE before stop, median/95p stop distance, average holding time, turnover/stop modification count, tail loss/worst gap or slippage event, regime stability;
- the listed ablations (swing confirmation, volatility/noise floor, order-flow veto, channel context, extremum/turning-point forecast, DeFi/cross-venue context, hysteresis/cooldown) are each removed and evaluated in turn;
- the experiment can conclude `NO_EDGE` and reject the policy if it only looks better visually without improving OOS economics or risk-adjusted outcomes.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
