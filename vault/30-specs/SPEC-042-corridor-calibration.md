---
id: SPEC-042-corridor-calibration
requirement: REQ-EXP-009
speckit_path: specs/042-corridor-calibration/spec.md
status: draft
---

## Summary

EXP-009's three corridor constructions — empirical residual quantile, parametric
band, and §13.8's conformal adjustment — measured forward from every fit and
judged by one metric: "target coverage with narrowest stable interval".

Both words carry weight. **Stable** means every fold: a corridor covering 95% in
one window and 65% in another averages to its target and is useless in both.
**Narrowest** is the tie-break among corridors that keep the promise, never a
consolation prize when none does — the narrowest of the corridors that miss is
still one that does not cover what it claims.

The conformal method calibrates on errors already observed and never on the one
it is about to be judged on. That leak is invisible in an aggregate report, which
is why the per-instant measurements are public: a test pins the instant its width
may first react to a shock.

Building it required the raw log slope [[ADR-049]] had named as missing.
`slope_normalized` cannot serve — it is divided by the residual spread, so two
channels with the same normalized slope move at different speeds, and a corridor
projected flat misses on one side however wide it is.

## Links

- Requirement: [[REQ-EXP-009]]
- Builds on: [[REQ-WP-006]], [[REQ-CHAN-001]], [[REQ-EXP-001]]
