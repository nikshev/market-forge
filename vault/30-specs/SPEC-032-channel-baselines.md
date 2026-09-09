---
id: SPEC-032-channel-baselines
requirement: REQ-CHAN-001
speckit_path: specs/032-channel-baselines/spec.md
status: draft
---

## Summary

PRD §13.3, §13.4 and §13.5 — the robust, quantile and Kalman channels — extracted
because [[REQ-EXP-001]] compares five models and only baseline A existed.

Each answers a different weakness of least squares. Huber's centre does not chase
a liquidation wick. The quantile channel can be asymmetric, which baseline A
cannot be: it places both bands as residual quantiles around one centre, so a
market that sells off hard and drifts up slowly gets a channel saying the two are
the same. The Kalman filter updates one observation at a time, and §13.5's single
forbidding sentence — "smoother that uses future observations is forbidden" — is
the design constraint, because the smoother is the better estimator and it reads
the future.

[[ADR-047]] records the one substantive decision: the quantile fit is solved
exactly by enumerating the lines through pairs of points, not descended. The
descent version reported a 2.5% channel on a perfectly flat series, and the
mutation sweep found it by way of a minimum-width guard that never bound.

## Links

- Requirement: [[REQ-CHAN-001]]
- Decision: [[ADR-047]]
- Builds on: [[REQ-WP-006]]
- Feeds: [[REQ-EXP-001]]
