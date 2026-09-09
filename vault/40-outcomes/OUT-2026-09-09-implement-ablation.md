---
id: OUT-2026-09-09-implement-ablation
step: implement
records: [REQ-US-006]
commit: null
---

## What was done

`channelflow.research.ablation`: REQ-US-006's five arms over one fold set, with
unrunnable arms named rather than scored. 13 tests.

This closes REQ-US-006.

## The reason named the symptom

The first implementation checked for a duplicate feature set before checking
whether a family had contributed anything. "Channel + DEX" resolves to the
channel's own features, so it reported as *a repeat of channel only* — true, and
useless. The absent DEX family, which is the whole reason the arm could not run,
did not appear in the report at all.

Reordered: a family that contributed nothing is the reason, checked first. The
duplicate branch still exists and still matters — two families can legitimately
resolve to one feature set through a taxonomy overlap — and now says something
different from the missing-family case, because they are different things.

## Three properties the fixture could not distinguish

The sweep found three survivors, all of the same kind:

- **the ranking's tie-break** — two arms over different features almost never
  score identically, so entry order and name order agreed on every input. Now
  `rank_arms` is public and tested on a constructed tie;
- **the feature overlap** — no fixture had a feature in two families, so listing
  it twice changed nothing. Funding is derivatives context and order flow both,
  which is the ordinary case;
- **`all_combined`** — the containment test compared it against `channel_only`
  alone, so an `all_combined` missing a family still passed. It now must contain
  every arm's families.

## What was decided

- **The folds are the caller's**, used as given. Rebuilding them per arm would
  make each arm's score depend on its own split.
- **An unrunnable arm never enters the ranking.** A ranking is an ordering of
  things that were measured.
- **A report with nothing runnable says so**, rather than presenting an empty
  ranking that reads like a completed comparison in which nothing won.

## Mutation results

Eight mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A family with no data is scored anyway | `test_an_arm_with_no_features_for_its_families_is_not_run` (+1) |
| Duplicates are scored as independent arms | `test_an_arm_identical_to_an_earlier_one_names_it` |
| Unrun arms enter the ranking | `test_an_unrun_arm_is_not_ranked` (+1) |
| The ranking tie-break is dropped | `test_two_arms_that_score_identically_rank_by_name` |
| An unknown family is accepted | `test_an_unknown_family_is_refused` |
| The ranking is worst-first | `test_two_arms_that_score_identically_rank_by_name` |
| An arm's features are not deduplicated | `test_a_feature_in_two_families_is_counted_once` |
| `all_combined` drops a family | `test_all_combined_contains_every_other_arms_families` |

## What is still open

- **Three of the five arms report as not run on today's registry**, which
  carries no channel or DEX features. That is the honest state, and the report
  says which family is missing rather than returning a number.
- **No CLI and no stored report.** PRD §38's `channelflow research` commands and
  §29's storage are both unbuilt.
