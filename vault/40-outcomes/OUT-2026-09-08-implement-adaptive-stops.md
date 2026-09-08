---
id: OUT-2026-09-08-implement-adaptive-stops
step: implement
records: [REQ-WP-020, REQ-BIAS-009]
commit: null
---

## What was done

`channelflow.stops`: PRD §44A.3's models, §44A.16's filter pipeline, §44A.28's
counterfactual replay with §44A.23's cost model and §44A.29's premature-stop
metric. 31 tests.

REQ-BIAS-009 moves to `implemented` — the last of PRD §41's rules that this
repository can currently close.

## Two mutations survived, and both found real gaps

- **Removing the post-buffer monotonic check changed nothing.** Every existing
  test's proposal was also caught by the initial-risk guard, so the two were
  indistinguishable. The case that separates them is a stop already tightened
  to 98 with an original contract at 95: a buffer pushing a proposal to 96
  *widens* risk against the current stop while staying inside the original
  contract, and only the monotonic check refuses it. That is the dangerous
  case, and it now has a test.
- **Removing `reasons`' minimum length changed no behaviour**, because every
  call site passes one. The guarantee is a type-level one and needed a
  type-level test — constructing the thing the constraint forbids.

Third time this pattern has appeared (REQ-WP-010, REQ-WP-012, here): two guards
over one property hide each other's absence, and only a case where exactly one
applies can tell them apart.

## What was decided

- **The filter order is the design.** Buffer, then monotonic, then market
  distance, then improvement threshold, then the initial-risk contract last.
  Checking monotonicity on the raw anchor rather than the buffered price would
  let a wide buffer push the stop the wrong way.
- **`_best_anchor` takes the tightest, not the nearest.** The point is to
  protect what the position has; a looser anchor that still tightens leaves
  risk on the table for no structural reason.
- **Naive baselines respect the monotonic rule too.** A baseline allowed to
  widen would not be a stop policy, and the comparison would be against
  something else entirely.
- **The clock check uses `time.monotonic`, not the bare word.** Every other
  package checks the bare word and that is fine there; here the domain rule is
  *called* monotonic tightening, so the word appears a dozen times in
  legitimate prose. A guard that fires on correct code gets weakened by
  whoever hits it next.

## Mutation results

Six mutations, all caught after the two gaps were closed, every restore
verified:

| Mutation | Caught by |
| --- | --- |
| A widening proposal is allowed | `test_a_buffer_may_not_loosen_the_stop_even_inside_the_initial_risk` |
| Anchors from the future are used | `test_an_anchor_from_the_future_is_never_used` |
| The data-quality freeze is ignored | `test_a_data_quality_freeze_holds_the_stop` |
| Realized R ignores fees and slippage | `test_realized_r_is_net_of_fees_and_slippage` (+1) |
| Slippage favours the position | `test_slippage_is_always_adverse` (+1) |
| A hold returns no reason | `test_a_proposal_cannot_be_built_without_a_reason` |

## What is still open

- **Items 16 to 18 of REQ-WP-020's ordering** — UI stop path, Telegram stop
  event, exchange reconciliation — are out of scope, and §44A.39 requires a
  separate acceptance process for live mode anyway.
- **Anchors are supplied, not gathered.** The policy takes `(price, known_at)`
  pairs; wiring REQ-WP-019's extrema, REQ-WP-006's boundaries and REQ-WP-012's
  nodes into an anchor builder is small and not done.
- **Slippage is modelled, not measured** ([[ADR-031]]).
