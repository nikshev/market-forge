---
id: OUT-2026-09-08-implement-volume-profile
step: implement
records: [REQ-WP-012]
commit: null
---

## What was done

`channelflow.volume`: PRD §14.1's trade-binned profile, POC, value area, nodes
and shape features, plus `volumeProfile.ts` and the chart overlay. 26 Python
tests, 5 TypeScript tests, 5 registered features.

## Two mutations survived, and both were my tests' fault

This is the run where mutation testing earned its keep.

- **A value area assembled by descending volume passed every test.** The
  `shelved` fixture's POC alone holds 20 of 26 units — more than 70% — so the
  value area is one bin under either construction, and the contiguity assertion
  was true for a reason that had nothing to do with the rule. Added a bimodal
  fixture where expansion gives `{0,1,2}` and descending volume gives
  `{0,2,4}`: both hold over 70%, and only one is a range.
- **Nodes measured against the whole profile passed every test.** The `shelved`
  fixture is five bins and the neighbour window is two either side, so
  "neighbours" and "everything" are the same set. Added a ten-bin monotonic
  ramp, which has no local structure at all but whose extremes are 1.8× and
  0.18× the profile mean.

Both tests now fail under their mutation. The lesson is the fixture's, not the
code's: a property that holds for every implementation on your fixture is not
being tested.

## What was decided

- **Bin assignment is integer division from a fixed anchor**, so arrival order
  cannot change the bins and a boundary trade always lands in the upper one.
- **The `ramp` test loosens `low_multiple` deliberately.** The first bin has
  neighbours on one side only, so its ratio is exactly the default threshold —
  flagged by an edge effect rather than by structure. The test says so rather
  than quietly choosing a fixture that hides it.
- **Skew is the volume asymmetry around the POC, not the third moment.**
  Calling the statistical moment "skew" here would invite comparison with
  numbers computed differently elsewhere; this is what a reader means when they
  look at a profile.
- **The chart draws bins as price lines, not a faked histogram.**
  lightweight-charts has no horizontal-histogram primitive, and stacking areas
  would put edges on the chart that do not mean what they look like — the same
  reasoning REQ-WP-009's channel zones follow.

## Mutation results

Six mutations, all caught after the two fixtures were fixed, every restore
verified:

| Mutation | Caught by |
| --- | --- |
| The value area takes bins by descending volume | `test_the_value_area_is_contiguous_on_a_bimodal_profile` |
| The POC tie-break takes the higher price | `test_a_tie_goes_to_the_lower_price_and_is_recorded` |
| Sides inferred rather than read from the aggressor | `test_sides_come_from_the_aggressor_never_from_bar_direction` |
| An empty window returns an empty profile | `test_an_empty_window_refuses` |
| Nodes measured against the whole profile | `test_nodes_are_relative_to_neighbours_not_to_the_whole_profile` |
| A shape feature loses its registration | `test_every_exposed_feature_is_registered` |

## What is still open

- **PRD §14.2's VWAP family and §14.3's volume anomaly** are named in the PRD
  and not in REQ-WP-012's acceptance criteria; not built.
- **Profile anchoring rules** (§14.1's rolling 4h/24h/7d, session, impulse) are
  the caller's choice of what to pass; the anchors themselves are unbuilt.
- **The chart overlay is labels, not bars.** Readable, and not what §27.2
  pictures; a proper histogram needs a custom series plugin.
