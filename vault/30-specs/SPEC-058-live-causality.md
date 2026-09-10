---
id: SPEC-058-live-causality
requirement: REQ-BIAS-002
speckit_path: specs/058-live-causality/spec.md
status: draft
---

## Summary

[[ADR-024]] gave PRD §41 rule 2 a home and refused to claim coverage for it "on
the strength of one engine's guard". That refusal was right, and this spec says
what the gap actually is.

Three mechanisms exist and none of them reaches a live feature. `require_causal`
has exactly one call site in the repository and it is inside a research
comparison. The forbidden-import scan reads `src/channelflow/extrema/` and no
other package, so `savgol_filter` in `features/flow.py` would pass every check
here. And `FeatureSpec.point_in_time_safe` is required on every registration
while no rule reads it — every feature happens to declare `True`, and a `False`
would be accepted in silence.

The rule names live features. Nothing checks the live features.

The work is to widen two existing guards rather than build a third. The design
decision worth reading twice is the default: **every package is scanned unless
it is explicitly exempt**, so a package added later joins the rule rather than
escaping it — the same inversion [[SPEC-057-experiment-gate-adoption]] used for
the research package, and for the same reason. The exemption is where a rule
like this erodes, so it carries a written reason and fails if it names a package
that no longer exists.

What this does not do is turn a declaration into a detection. [[ADR-022]] settled
that a general detector is not achievable, and `causality.py` already says a
transform peeking forward while declaring itself causal is Test A's business.

## Links

- Requirement: [[REQ-BIAS-002]]
- The refusal this closes: [[ADR-024]]
- Declaration over detection: [[ADR-022]]
- Registry as a gate: [[ADR-015]]
- Same inversion, different rule: [[REQ-BIAS-011]]
