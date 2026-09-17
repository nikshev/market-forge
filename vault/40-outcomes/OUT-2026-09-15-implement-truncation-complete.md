---
id: OUT-2026-09-15-implement-truncation-complete
step: implement
records: [REQ-NRT-LEAK]
commit: null
---

## What was done

Closed PRD §35.4. **All 55 registered features are accounted for: 39 cases and
16 refusals.** [[REQ-NRT-LEAK]] reaches `implemented`, and rule R5 — the one this
project never waives — now reaches both §35.3 and §35.4.

This cycle added `defi` (2 cases) and `volume_structure` (5 refusals), and the
mechanical check that makes the refusals honest.

## What was decided

**A refusal must be earned by a signature, not by assertion.** Sixteen of
fifty-five is a large fraction — larger than the spec expected — so the refusal
list is now *checkable* rather than merely claimed:
`test_a_refusal_is_only_available_to_a_feature_that_names_no_moment` inspects
every producer behind a refused feature and fails if any takes an `at_ns` or
`as_of_ns` parameter. A feature whose producer names a moment could have had a
case, and the refusal would be a way out.

That test is what stops the mechanism becoming the requirement. Without it,
"refused" is a word somebody types.

**The two families split cleanly, and the split is the finding.** Every producer
in `defi` takes a moment — `swap_imbalance(swaps, *, as_of_ns, window_ns)`,
`active_liquidity_at(readings, *, at_ns)` — so both features get real cases.
Nothing in `channelflow.volume` names a moment anywhere; `build(trades, *,
bin_width, …)` is a pure function over a list the caller scopes. So the
point-in-time choice for those five lives in the caller, not the feature.

**What the refusals actually tell you.** They are not gaps. They identify where
the point-in-time risk lives for 16 features: in the code that decides what to
hand them. That is a finding about the registry's shape — some features carry
their own time semantics, some do not — and it is now written down where the
suite reports it.

## The whole of §35.4, as it landed

| family | cases | refusals |
|---|---|---|
| `derivatives` | 19 | — |
| `order_book` | 4 | 11 |
| `trade_flow` | 5 | — |
| `order_flow` | 5 | — |
| `channel` | 4 | — |
| `volume_structure` | — | 5 |
| `defi` | 2 | — |
| **total** | **39** | **16** |

One real leak found and fixed along the way: `WallTracker.observe` attributed
volume from trades after its own `as_of_ns`. Two registered features, both
declaring `point_in_time_safe: True`.

Mutation sweeps across the truncation machinery, the derivatives seam, the flow
and OFI windows, the liquidation filters and the new wall filter: **18 caught, 0
survived** on the three specifications re-run here, with every earlier sweep
green at the time it was written.

## What is still open

**§35.5 (live/replay parity)** is the last section of this family with no
requirement note. [[REQ-NRT-E]] covers replay parity for extrema only.

**Eleven refusals would become cases** if a point-in-time read were added to
`BookService`. It already has one — `service.health(as_of_ns)` — so the shape is
not foreign to the class, and the refusal reason names exactly what would have to
change.
