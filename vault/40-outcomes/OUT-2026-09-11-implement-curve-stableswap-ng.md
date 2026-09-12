---
id: OUT-2026-09-11-implement-curve-stableswap-ng
step: implement
records: [REQ-WP-046]
commit: null
---

## What was done

`tools/record/evm.py`, `tools/record/curve_capture.py`, two chain-read fixtures
and `dex/curve.py` — Curve's family classification and the Stableswap-NG quote,
ported from `CurveStableSwapNGViews.get_dy`.

[[REQ-WP-046]] stays `tested`: this is the Stableswap-NG half. Cryptoswap is the
second.

## Sixty quotes, sixty exact, first attempt

Four live pools at one pinned block, including a three-coin pool across all six
ordered index pairs and sizes spanning four decades. Every one equals the pool's
own `get_dy` exactly — §18.25 asks for "within tolerance", and integer
arithmetic allows the stronger claim.

Three things in that quote are easy to get plausibly wrong, and each is now
asserted on its own rather than left to the sixty:

- **The fee denominator is 1e10**, not the 1e6 every other venue in this project
  uses. Wrong by ten thousand, in the direction of charging nothing.
- **The effective fee is not the base fee.** Stableswap-NG scales it by how far
  off peg the two coins sit. All four pools have the multiplier switched on.
- **Balances are not what the invariant sees.** Each coin carries a stored rate
  folding in its decimals and, for an accruing token, its exchange rate.

## The classification cost two wrong guesses, and that was the point

The first design used `base_pool()` to spot a metapool, with
`get_dy_underlying` as a backup. **Neither survives contact with live pools:**
no metapool answers the first, and the original 3pool answers the second,
having inherited a lending-pool interface it does not use.

What actually makes a metapool is that one of its coins is another pool's LP
token — a fact about the registry rather than the pool — so it comes from
Curve's MetaRegistry, resolved through the immutable AddressProvider rather than
hardcoded.

Both discarded discriminators are now asserted **absent** from the capability
set, because they are the first thing a reader would reach for.

One subtlety survives from the capture tool all the way to the classifier: a
registry that does not know an address is saying *this is not a Curve pool*, and
storing that as `false` alongside every genuine non-metapool turns it into *a
Curve pool that is not a metapool*. It is a third state, and it stays one.

Nine live contracts classify correctly, one of them not a pool at all.

## What the probe found out about the probe

**A contract with a payable fallback answers every selector.** WETH returns `0x`
to any calldata rather than reverting, so a capability probe that only caught
reverts would report that WETH implements all of Curve. Empty return data is
"no" too, and separately so.

**A revert and a refusal had to become different exception types.** The first
probe run returned nothing at all for eight of nine contracts. The cause: a
probe expects most of its calls to revert, ran them at full speed, was rate
limited, and every endpoint went into cooldown — while the caller, catching one
exception type for both, read the resulting quorum failure as "this pool does
not answer that". A working probe reporting a wrong answer, silently.

So `tools/record/evm.py` now exists: the shared machinery, with the lessons all
three capture tools learned written down once. A revert is `Reverted` and a
refusal is `Refused`; the pause between calls applies to both; a pool that is
momentarily short of a quorum waits for the soonest cooldown instead of failing
the run; and eight endpoints are listed rather than two, because a few hundred
calls will lose one.

## Depth, by simulation

§18.9.1 forbids a derived tick map twice over, so depth is quote simulation
across a notional grid and bisection for the inverse. Two choices worth naming:

- **The arithmetic is `Fraction`, not float.** Slippage of a few basis points on
  a stable pool is the entire signal, and it is the first thing binary floating
  point rounds away.
- **An unreachable target says so**, rather than returning the largest notional
  tried — [[ADR-036]]'s distinction for the concentrated-liquidity curve, for
  the same reason.

The probe size and the search ceiling are the caller's, with no defaults: "small"
and "large enough" are facts about a coin's decimals, and a default would
silently report "unreachable" for a pool it was too small for.

## Two branches nothing reaches, handled differently

- **`newton_y`'s underflow guard was deleted.** The contract computes
  `2y + b - D` in `uint256`, where an underflow reverts; it cannot underflow,
  because the search starts at `y = D` where the denominator is `D + b > 0` and
  every later iterate sits above the positive root. Six hundred thousand
  generated inputs agree. A guard for it would be a branch no test can honestly
  cover.
- **`newton_y`'s non-convergence raise was kept**, and its mutant survives. The
  same six hundred thousand inputs never exhaust the 255-round budget, so the
  branch is unreachable in practice — but unlike the underflow, it cannot be
  *proved* unreachable, and removing it would trade a refusal for a silently
  wrong estimate. An uncaught mutant is the right price.

The `get_D` tolerance went the other way. Replacing "settles within one" with
"settles exactly" survived every fixture pool, so four hundred thousand pools
were searched for one that oscillates by exactly one forever. It exists, and it
is now a fixture: the tolerance is a rounding fact, not a loose comparison, and
tightening it turns a pool that quotes perfectly well into one that refuses.

## What the sweep found besides that

Thirty-five mutations, thirty-four caught. The two that survived the first pass
were both gaps in the tests rather than in the code, which is the usual result:

- **A search that reported the notional it found alongside the slippage it
  measured at the search bound** passed every assertion, because the assertion
  was "the slippage reaches the target" and the bound's slippage does too. The
  test now checks that the reported numbers describe the reported notional.
- **Deleting the "a probe of nothing prices nothing" guard** passed, because a
  probe of zero falls through to the "bought nothing" branch, whose message also
  mentions the probe. A *negative* probe falls through to a negative price with
  no error at all, which is what the test now asserts against.

## A process failure worth recording

The first sweep hung on a mutant that turned the bisection into an infinite loop,
and **left the mutant in the working tree.** The next twenty minutes went to
diagnosing a test suite that had passed in 0.16 seconds an hour earlier —
against code nobody had written.

The sweep script now restores the source in a `finally`, and counts a hang as
caught: a mutant that hangs is one the suite would never let through.
