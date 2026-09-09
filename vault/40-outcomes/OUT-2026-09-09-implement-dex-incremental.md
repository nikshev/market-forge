---
id: OUT-2026-09-09-implement-dex-incremental
step: implement
records: [REQ-EXP-007]
commit: null
---

## What was done

`channelflow.research.dex_incremental`, and the cumulative machinery extracted
from [[REQ-EXP-004]] into `cumulative.py`. 9 tests, nine mutations, all caught.

## One character of prefix

The DEX price-divergence family was declared with the prefixes
`("dex_divergence_", "basis_")`. The second matched `basis_bps` — PRD §16's
perp-spot basis, a CEX derivatives feature that has been registered since
[[REQ-WP-013]].

So the "CEX + DEX price divergence" arm would have scored a CEX number and
reported its contribution as the DEX view's: the experiment would have answered
a different question, plausibly, with a real number.

It surfaced because the registry-state test pins exactly which families are
empty rather than asserting a count. A test that had checked "at least one DEX
family is empty" would have passed.

## What was decided

- **The not-run state is a test, not a comment.** When the DEX features are
  registered, `test_every_dex_family_is_empty_in_the_registry_today` fails and
  names what to update.
- **The scoring path is exercised with supplied features**, so the module is
  observed in both states rather than only in the one today's registry produces.
- **The instrument is required and reported.**

## Mutation results

Nine mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The arms are not cumulative | `test_the_divergence_family_shows_its_increment` (+1) |
| The instrument is optional | `test_the_instrument_is_required` |
| The instrument is not reported | `test_the_report_names_the_instrument` |
| The divergence family matches the perp basis | `test_every_dex_family_is_empty_in_the_registry_today` (+1) |
| The taxonomy is not passed to the arms | the arms fail to construct |
| The registry is read cold | `test_the_families_resolve_in_a_process_that_imported_nothing_else` (+1) |
| The increment is taken the other way round | `test_the_divergence_family_shows_its_increment` (+1) |
| An increment over an unscored arm is zero | `test_an_increment_over_an_unscored_arm_is_absent_not_zero` |
| The added features are not computed | `test_each_increment_names_what_it_added` (+1) |

## What is still open

- **The DEX features are unregistered**, which is the whole of what four arms
  are waiting on. PRD §19 registration for [[REQ-WP-015]]'s and
  [[REQ-WP-016]]'s outputs is separate work.
