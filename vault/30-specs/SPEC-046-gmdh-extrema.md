---
id: SPEC-046-gmdh-extrema
requirement: REQ-EXP-013
speckit_path: specs/046-gmdh-extrema/spec.md
status: draft
---

## Summary

EXP-013 weighs the derivative route to an extremum against the cheap one. Four
arms — a direct classifier, a GMDH direct classifier, the GMDH forward path with
its derivative roots, and an ensemble of the direct probability and the root's
stability — run over one set of folds and one design matrix, and report seven
numbers.

Five of those seven are about the derivative route specifically, and two of them
are reported as *absent* for the classifier arms. That absence is the finding:
a classifier outputs a probability and never names a time or a price, and naming
both is precisely what the four networks, the promotion gate and the
perturbation lattice are being paid for. Filling those columns in from somewhere
else would judge the cheap arm on a promise it never made.

The denominators turned out to be the whole design problem, and [[ADR-051]]
records them. A root's presence rate averaged over rows whose forward path never
turned measures how often the market turns, not how stable a turn is — on the
first fixture built here that alone read 0.50 against the gate's 0.70 and
reported "unstable" about roots that were stable in every member of every
lattice.

The verdict is EXP-013's own last sentence made mechanical, and it names every
failure rather than the first: an experiment that reports one reason at a time
costs a full re-run per reason.

## Links

- Requirement: [[REQ-EXP-013]]
- Decision: [[ADR-051]]
- Builds on: [[REQ-WP-018]], [[REQ-WP-019]], [[REQ-BT-001]], [[REQ-US-007]]
