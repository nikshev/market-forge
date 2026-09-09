---
id: OUT-2026-09-09-implement-scored-markets
step: implement
records: [REQ-US-001, REQ-US-004]
commit: null
---

## What was done

The market list is ordered by PRD §43's rank score, and a signal's detail
carries §22.4's explanation into a panel showing all six of §22.1's groups.
10 API tests and 4 panel tests.

This closes the first two user stories. [[REQ-US-001]] wanted the list "sorted
by setup score, so that I can quickly find the most interesting situations";
[[REQ-US-004]] wanted the contribution factors shown.

## A tie nothing was breaking

The sweep found that removing the name tie-break on the unscored tail changed no
test. The fixture held one unscored market, so the tie never occurred — the code
was right and nothing was checking it. A second unscored market, added after the
first in the repository but before it by name, now makes the property
observable.

That is the same shape as the two survivors in [[REQ-SCORE-001]] the day before:
a property that holds, over a fixture that cannot tell whether it holds.

## What was decided

- **An unscored market sorts after every scored one and reports nulls.** Ranking
  it at zero would place it among the worst setups and say it had been examined
  and found weak.
- **A missing family is missing, never negative.** The panel that merges them
  turns an outage into a reason.
- **The panel renders the six groups from a constant.** Rendering whatever
  arrived cannot show an absence, because the absent group is the one the
  response does not mention.
- **The explanation is not nested with the outcome**, per §27.4.

## Mutation results

Eight mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Unscored markets rank at zero instead of last | `test_the_order_is_the_same_twice` (+1) |
| The unscored tail keeps repository order | `test_the_unscored_tail_is_ordered_by_name` |
| Ranking ignores liquidity | `test_the_market_list_is_ordered_by_rank_score` (+1) |
| The list is ordered by setup score, not rank score | `test_the_market_list_is_ordered_by_rank_score` (+1) |
| An unscored market reports a zero score | `test_an_unscored_market_sorts_last_with_null_scores` |
| The confidence is dropped from the row | `test_a_market_carries_the_confidence_beside_its_score` |
| Missing families are dropped from the explanation | `test_a_scored_signals_detail_carries_its_explanation` (+1) |
| The explanation is never attached | `test_the_outcome_stays_separate_from_the_explanation` (+1) |

## What is still open

- **Nothing writes scores yet.** The API serves what the pipeline stored, and
  the pipeline does not store one — so on a live system today every market
  sorts into the unscored tail. That is the honest state, and it is visible
  rather than hidden behind a zero.
- **One score per market, its latest.** A history is PRD §29's storage work.
