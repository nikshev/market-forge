---
id: SPEC-063-research-run
requirement: REQ-WP-024
speckit_path: specs/063-research-run/spec.md
status: draft
---

## Summary

Five mechanisms exist and nothing calls any of them. A `RunIdentity` is never
assembled; the field seam is never reached from production code; no path fits a
model and registers its artifact; calibration per horizon has no caller. Each
was recorded honestly as an open question, and each answered it with "a caller
will do it".

This is that caller, for [[REQ-EXP-008]]'s comparison.

The reason it is one requirement rather than five wires: **every one of those
mechanisms refuses something** — a dirty tree, an unregistered artifact, a
variant missing from its own field, a horizon too thin to speak. Separately each
refusal is theoretical. Assembled, they decide whether a result may be reported
at all, and a run that fails says which component stopped it.

Two decisions carry the design.

**The comparison reports what it fitted; the run does not refit.** Obtaining an
artifact hash by fitting a second time would be a second scoring path, and this
repository has refused that wherever it has come up — a comparison is only honest
if one code path produced both numbers. `Score` gains an optional artifact, so
the two experiments that supply their own predictions report none rather than a
false one.

**A variant's artifact covers its folds together.** A variant is fitted once per
fold, and what a result cites is the variant *as run*. Registering each fold
separately would produce artifacts nothing cites and leave the run's own identity
ambiguous.

## Links

- Requirement: [[REQ-WP-024]]
- The five it calls: [[REQ-REPRO-001]], [[REQ-BIAS-011]], [[REQ-WP-022]], [[REQ-WP-023]], [[REQ-PIPE-001]]
- The experiment wired: [[REQ-EXP-008]]
