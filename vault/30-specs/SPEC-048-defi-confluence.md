---
id: SPEC-048-defi-confluence
requirement: REQ-EXP-015
speckit_path: specs/048-defi-confluence/spec.md
status: draft
---

## Summary

EXP-015 asks whether OI, funding and liquidations, the DEX-CEX executable basis,
DEX depth asymmetry, swap imbalance and LP liquidity migration improve
turning-point probability. Two words in the requirement carry it — *strict
ablation* and *same walk-forward folds* — and both are things the code refuses
to run without rather than sentences in a method section.

Strict means every arm is one family from the baseline or one family from the
full set. `strictness_violations` is public because that property cannot be
verified by reading a table of numbers: an arm two families from both references
still produces a delta, and the delta still looks like one family's
contribution.

Each family is read twice, added to the baseline alone and removed from the full
set, because the two disagree whenever families overlap — which for derivatives
and DeFi context is most of the time. A family that helps alone and adds nothing
to the full set is carrying information something else already carries, and a
single-direction ablation reports whichever of those two facts it happened to
measure.

Same folds means one certified dataset, used as given, and a fingerprint the
report carries. The fingerprint holds the spans and not just the count: two
studies over different rows can both use three folds, and that is the exact case
the requirement excludes.

## Links

- Requirement: [[REQ-EXP-015]]
- Builds on: [[REQ-US-006]], [[REQ-EXP-004]], [[REQ-EXP-007]], [[REQ-WP-019]]
