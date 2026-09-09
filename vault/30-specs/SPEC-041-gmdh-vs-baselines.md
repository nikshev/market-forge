---
id: SPEC-041-gmdh-vs-baselines
requirement: REQ-EXP-008
speckit_path: specs/041-gmdh-vs-baselines/spec.md
status: draft
---

## Summary

EXP-008 names four models and four metrics, and two of the models were the ones
[[ADR-029]] deliberately left out. [[ADR-050]] records how they were built so
that ADR-029's objections are answered rather than overruled.

The elastic net's penalty and L1 ratio are required arguments — ADR-029's
objection was the coefficient, not the arithmetic, and a default would be that
coefficient chosen by the module and then hidden. The boosted trees are
depth-limited by construction: a booster of stumps is additive in its features
and cannot represent an interaction, which is the only reason §23.6 asks for a
tree, and a GMDH model beating that baseline would be beating something
structurally blind.

The four metrics each answer a way a model can look good and be useless.
Calibration asks whether a 0.7 means seven in ten. PR-AUC rather than ROC-AUC,
because these targets are imbalanced. Expectancy by bucket is where calibration
meets money. Feature stability asks whether the model found the market or the
fold.

## Links

- Requirement: [[REQ-EXP-008]]
- Decision: [[ADR-050]], amending [[ADR-029]]
- Builds on: [[REQ-WP-018]], [[REQ-BT-001]]
