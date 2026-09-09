---
id: OUT-2026-09-09-implement-multi-scale-extrema
step: implement
records: [REQ-EXP-016]
commit: null
---

## What was done

`channelflow.research.multi_scale`: EXP-016's three nesting rules, each priced
against the same candidates without it. 17 tests, sixteen mutations, all caught.

## The arithmetic behind "not visual appeal"

EXP-016 ends with a warning rather than a metric, and the warning is about a
specific piece of arithmetic. A filter improves the average trade almost by
definition — that is what a filter does — and it can lose on the total, because
it removed winners along with losers. A chart of the survivors shows the first
effect perfectly and cannot show the second, because the removed trades are not
on the page.

The fixture built here makes both cases real. Being inside the higher zone
decides the outcome, so that rule keeps half the candidates and more than
doubles the average trade — enough to come out ahead in total as well. Alignment
with the higher slope adds a hair to the average and takes half the book away to
do it, so the total falls. Both are selective, both look identical on a chart,
and the report names the difference.

## One number that was doing two jobs

The improvement floor had been applied to the per-trade delta and to the total
delta alike, and those are not comparable quantities: one is R per trade and the
other is a sum of R over sixty trades. A single constant held against both is a
number meaning two different things, which is the sort of thing that reads fine
until someone changes the fixture size.

The floor now guards the per-trade number, which is the one a filter inflates by
construction and where a small positive difference is what rounding looks like.
The total is the book's own outcome over the same candidates: if it went up, it
went up.

## The look-ahead this experiment would lose if it lost one

A five-minute candidate at 10:07 sits inside a fifteen-minute bar that closes at
10:15. That bar's zone is partly made of what happened after the candidate, and
using it improves every number in the module while nothing about any of them
looks wrong. `available_frame` takes the last frame with `closed_ns <= as_of_ns`
and is public so the property is testable on its own; frames out of closing
order are refused, because out of order "the last frame that had closed" is
whichever one happened to be last in the list.

## Three survivors

The floor, described above. And two of the ordinary kind: every candidate in the
main fixture sits well inside the zone, so an exclusive upper bound changed
nothing measurable; and no test read the multi-scale rule's composition, so
swapping its conjunction for a disjunction produced a rule that was merely
looser than intended and still scored. Both now have their own cases — a
candidate at each edge of the zone, and a candidate satisfying one scale only,
tested in both directions.

## Mutation results

Sixteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A rule is dropped | `test_the_three_rules_the_prd_names_are_evaluated` |
| An unknown rule is accepted | `test_a_rule_outside_the_three_is_refused` |
| The frame containing the candidate is visible | `test_only_a_closed_higher_frame_is_visible` |
| Out-of-order frames are accepted | `test_frames_out_of_closing_order_are_refused` |
| The total is not reported | `test_a_rule_that_earns_its_selectivity_is_named_as_such` |
| The reading ignores the total | `test_a_rule_that_looks_better_than_it_is_is_named_as_such` |
| The reading ignores the average trade | `test_a_rule_that_helps_neither_way_is_named_as_such` |
| The improvement floor is ignored | `test_the_improvement_floor_decides_what_counts_as_an_improvement` |
| An empty kept set has zero expectancy | `test_a_rule_that_keeps_nothing_has_no_expectancy` |
| The rejected set is not measured | `test_the_rejected_candidates_are_reported_too` |
| A candidate without context still counts in the base | `test_a_candidate_without_context_is_excluded_from_every_arm` |
| The multi-scale rule needs only one scale | `test_multiple_scales_means_both_of_them` |
| The zone bound is exclusive on one side | `test_the_zone_includes_its_own_edges` |
| Alignment ignores the direction | `test_a_rule_that_looks_better_than_it_is_is_named_as_such` |
| An invalid direction is accepted | `test_a_direction_that_is_neither_long_nor_short_is_refused` |
| The improvement floor may be zero | `test_the_improvement_floor_is_required_and_positive` |

## What is still open

- **No rule is selected.** The fixtures are analytic and establish that the
  evaluation can produce each of its four readings, not what it produces on real
  bars.
- **The improvement floor is unvalidated** and the per-trade reading moves with
  it.
- **The three rules are the PRD's three.** "Directional-change thresholds at
  multiple scales" is implemented as the conjunction of the other two, which is
  a reading of the phrase rather than a separate detector at each scale — a
  real multi-scale threshold study would run [[REQ-WP-019]]'s detector at each
  timeframe and is a larger piece of work than EXP-016 asks for here.
