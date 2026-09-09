---
id: OUT-2026-09-09-implement-defi-confluence
step: implement
records: [REQ-EXP-015]
commit: null
---

## What was done

`channelflow.research.defi_confluence`: EXP-015's strict ablation over five
derivatives and DeFi families, read in both directions on one fold set. 15
tests, fifteen mutations, all caught.

## Two adjectives made into refusals

EXP-015's requirement is two sentences of families and one sentence of method:
"use strict ablation and same walk-forward folds". Both halves of that sentence
describe failures that produce perfectly ordinary-looking numbers.

**Strict.** An ablation whose arms differ in two things still yields a delta per
arm, and the delta still gets written down under one family's name. It is the
sum of two contributions and attributable to neither. So the arms are generated
— the baseline, each candidate added alone, the full set, each candidate removed
— and `strictness_violations` refuses a set that is not one family from either
reference. It is public because that property cannot be checked by reading the
output.

**Same folds.** The failure here is a per-family study run separately with the
numbers put in one table, and nothing about those numbers looks wrong. Each
report carries the fingerprint of its fold set and `require_same_folds` refuses
a comparison across two.

## Two survivors, and both were fixtures that could not reach the guard

The fingerprint's spans never mattered, because the only pair of datasets
compared also differed in their fold *count* — so a fingerprint carrying nothing
but the count separated them anyway. A second pair, three folds each over
different rows, is the case the requirement is actually about.

And no fixture produced a difference in the band between zero and the floor, so
"any improvement counts" agreed with the floor on every row. Running the same
data at a floor of 0.9 Brier separates them: at that floor nothing counts as
helping, including the family that genuinely improves the score by a quarter of
a point.

## The reading that needed two directions

The fixture has one family that duplicates another exactly. Added to the
baseline alone it improves the Brier score by 0.255; removed from the full set
it costs 0.0007. Those are the same family, and a single-direction ablation
reports whichever of the two it happened to run. The report names that case —
"adds alone but nothing to the full set" — and lists the families in it.

## What was decided

- **The two directions share a sign convention.** The removal delta is negated
  so that in both columns a negative number means the family helped; two columns
  with opposite conventions is a footnote nobody reads twice.
- **An unmeasured family is not a worthless one.** A family whose arm did not run
  reads as unmeasured, and its increment is absent rather than zero.
- **The instruments are named and checked.** EXP-015 says "BTC/ETH and other
  liquid assets"; a report naming an asset it never scored is a claim about that
  asset.

## Mutation results

Fifteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A family is dropped | `test_the_five_families_the_prd_names_are_ablated` |
| The leave-one-out arms are not built | `test_every_arm_is_one_family_from_a_reference` |
| Strictness is not checked | `test_an_arm_two_families_from_both_references_is_refused` |
| An arm two families away passes the check | `test_an_arm_two_families_from_both_references_is_refused` |
| The fold fingerprint ignores the spans | `test_the_fingerprint_tells_apart_fold_sets_of_the_same_size` |
| Reports on different folds may be compared | `test_reports_on_different_folds_cannot_be_compared` |
| The in-context direction is not measured | `test_a_family_is_measured_both_alone_and_in_context` |
| The in-context sign is not flipped | `test_a_family_is_measured_both_alone_and_in_context` |
| An unmeasured family reads as adding nothing | `test_a_family_with_no_features_is_unmeasured_rather_than_worthless` |
| A missing arm's delta is zero | `test_a_family_with_no_features_is_unmeasured_rather_than_worthless` |
| The improvement floor is ignored | `test_the_improvement_floor_decides_what_counts_as_an_improvement` |
| The instruments are not checked against the data | `test_the_instruments_are_required_and_checked_against_the_data` |
| An empty instrument list is accepted | `test_the_instruments_are_required_and_checked_against_the_data` |
| The improvement floor may be zero | `test_the_improvement_floor_is_required_and_positive` |
| The DEX basis family claims the CEX perp basis | `test_the_dex_basis_family_does_not_claim_the_cex_perp_basis` |

## What is still open

- **None of the four DEX families has a registered producer.** The prefixes are
  declared and `available_from_registry` resolves them to nothing, so a run
  against the live registry would report four families unavailable — which is
  the honest answer and not a result.
- **The improvement floor is unvalidated** and every reading moves with it.
- **The fixtures are analytic.** They establish that the ablation can produce
  each of its four readings, not what it produces on real books.
- **This module costs 15 seconds on every commit.** Twelve arms times three
  folds times four baselines apiece; it was 71 seconds before the fixture was
  cut from 160 rows and four folds to 60 and three.
