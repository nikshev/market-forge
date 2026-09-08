---
id: OUT-2026-09-08-implement-uniswap-v3
step: implement
records: [REQ-WP-015]
commit: null
---

## What was done

`channelflow.dex`: PRD §18.7's price math, event model, state reconstruction
and §18.7.1's executable depth curve. 42 tests.

## A comparison between different currencies

`DepthCurve.asymmetric_at` compared token1 spent going up against token1
*received* going down — two different quantities — and duly reported every band
of a perfectly symmetric pool as lopsided. The guard test caught it
immediately: a curve that always reports asymmetry is noise, and noise gets
muted.

Costs are now expressed in one token, using the pool's own spot price, and a
tolerance covers the half-percent that square-root price space makes
unavoidable even at constant liquidity: moving +50 bps and −50 bps are not
mirror images, and a zero tolerance would call every pool asymmetric for a
reason that has nothing to do with its liquidity.

## What was decided

- **The single-range depth test checks the walk against the closed form**
  computed independently in the test. Where the walk has nothing to walk, the
  two must agree — otherwise the traversal is being tested against itself.
- **The crossing test uses two pools identical but for one boundary.** A test
  asserting a number would pass whatever the traversal did; asserting that
  crossing a boundary makes the same move *cheaper*, because there is half the
  liquidity beyond it, is a claim about the mechanism.
- **Tick round trips are tested at ±887,000**, near the contract's own bounds,
  where `1.0001^tick` is around 10^38. A float implementation loses the round
  trip long before that.
- **`rebuild` returns a new state** rather than mutating, so a caller holding
  the previous one for §18.7.2's integrity comparison still has it.

## Mutation results

Seven mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Events ordered by block alone | `test_events_are_applied_in_canonical_order_not_arrival_order` (+1) |
| A duplicate log is deduplicated | `test_a_duplicate_log_is_refused` |
| A mint adds at both ticks | `test_a_mint_adds_at_the_lower_tick_and_subtracts_at_the_upper` |
| Every range changes active liquidity | `test_a_range_away_from_the_current_tick_does_not` (+1) |
| `Collect` changes liquidity | `test_collect_leaves_liquidity_untouched` |
| An unreachable target returns what it consumed | `test_a_target_beyond_known_liquidity_is_unreachable` (+1) |
| The traversal never changes liquidity at a crossing | `test_crossing_a_tick_changes_the_liquidity_used` |

The first is PRD §18.7's named trap, and sorting by block alone is exactly what
a timestamp sort degenerates to.

## What is still open

- **Uniswap v4, Curve, Aerodrome and Hyperliquid** (§18.8 to §18.11).
- **No ABI byte decoding.** The adapter takes decoded field values; unpacking
  `data` belongs to a codec behind REQ-WP-014's registry.
- **No fee accounting**, and **depth is in pool tokens rather than USD**.
- **The depth walk is linear in initialized ticks.** A pool with thousands
  would want an indexed traversal; PRD §0.14 puts correctness first.
