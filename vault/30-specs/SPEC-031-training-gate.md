---
id: SPEC-031-training-gate
requirement: REQ-US-007
speckit_path: specs/031-training-gate/spec.md
status: draft
---

## Summary

REQ-US-007 asks for "a guarantee that the training dataset contains no feature
leakage". Every check that guarantee needs already existed in [[REQ-WP-017]]'s
`leakage.py`, and already ran — in tests, by hand, wherever someone chose to call
them. A check someone has to remember is not a guarantee, and the failure it
misses is silent: a dataset whose labels were knowable at `t` trains fine, scores
well, and every metric downstream reads like an edge.

So the check becomes the only way to obtain the thing training accepts. A
`CertifiedDataset` cannot be constructed around an unclean report, and the three
training entry points — the direct baseline, the derivative experiment, the
ablation — take one instead of a fold list. The certificate holds its own folds,
so a caller who certifies and then edits their list cannot train on something the
certificate does not describe.

This is the fourth time this repository turns a prohibition nobody can verify
into a structure that cannot be violated: [[ADR-022]]'s transform declaration,
[[ADR-027]]'s inert regime label, [[ADR-040]]'s lead-lag import ban, and this.

## Links

- Requirement: [[REQ-US-007]]
- Builds on: [[REQ-WP-017]], [[ADR-025]]
- Enforced at: [[REQ-WP-018]], [[REQ-WP-019]], [[REQ-US-006]]
