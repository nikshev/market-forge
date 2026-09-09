---
id: OUT-2026-09-09-implement-volume-confluence
step: implement
records: [REQ-EXP-005]
commit: null
---

## What was done

`channelflow.research.volume_confluence`: EXP-005's classification and its
three-valued answer. 14 tests, eleven mutations, all caught on the first sweep.

## A control that was not one

The test for "a boundary away from every level" used a price of 102.5, inside a
thin bin of the constructed profile. That bin *is* a low-volume node, and EXP-005
counts LVNs among its levels — so the classifier was right and the test was
wrong. A boundary hanging over a gap is precisely the proposition the question
is about.

The control is now a price where nothing traded at all, which is neither a node
nor an edge.

## What was decided

- **The effect size is required.** A test reads `inspect.signature` and asserts
  it has no default: "materially" is the question, and a default answers it on
  the researcher's behalf.
- **Three verdicts.** A study that could only find an effect would find one.
- **Timeouts are counted and are not decisions.** Target-before-stop is a
  probability over setups that reached one or the other, and folding timeouts
  into the denominator makes a quiet market look like a losing one.
- **A population that decided nothing refuses.** That is different from a
  probability of zero.

## Mutation results

Eleven mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The value-area edge is ignored | `test_a_boundary_at_the_value_area_edge_is_confluent` (+1) |
| Nodes are ignored | `test_a_boundary_on_a_high_volume_node_is_confluent` |
| The band is ignored | `test_the_band_decides_how_close_counts` (+1) |
| The verdict never says lower | `test_a_lower_probability_with_confluence_is_reported_as_lower` |
| The effect size is ignored | `test_a_small_difference_is_not_materially_different` (+1) |
| The difference is taken the other way round | `test_the_same_difference_flips_the_verdict_when_the_effect_size_changes` (+1) |
| Ambiguous outcomes are kept | `test_ambiguous_outcomes_are_excluded_and_counted` |
| Timeouts count as decisions | `test_timeouts_are_counted_but_are_not_decisions` (+1) |
| The small-population guard is dropped | `test_a_population_too_small_refuses` |
| A population that decided nothing returns zero | `test_a_population_that_decided_nothing_refuses` |
| A negative effect size is accepted | `test_a_negative_effect_size_is_refused` |

## What is still open

- **No real setups.** The study is the procedure; producing observations for a
  live venue is pipeline work.
- **Confluence is one flag.** Whether an HVN boundary behaves differently from
  an LVN one is a finer question, and a different experiment.
