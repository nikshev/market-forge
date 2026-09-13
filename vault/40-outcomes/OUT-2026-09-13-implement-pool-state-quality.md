---
id: OUT-2026-09-13-implement-pool-state-quality
step: implement
records: [REQ-WP-060]
commit: null
---

## What was done

`dex/reconstruction.py`, `tables/dex_state.py`, a fixture of real mainnet logs,
and a guard inside §18.7.1's traversal. 22 tests, **18 of 18 mutants caught**.

## The blocker was described wrongly, and that is the finding

Phase 4 said the `LiquidityState` table "waits for something that reconstructs a
pool state". Something does: [[REQ-WP-015]]'s `dex/pool.py` has applied §18.7's
ordered events, kept the sparse tick map and refused duplicate logs since it was
written. What was missing was the reconstruction's opinion of itself.

That distinction is the whole requirement, because **the state's two halves
behave completely differently under a partial replay.** Every `Swap` reports the
pool's `liquidity`, so active liquidity self-heals at the first swap of any
window. The tick map holds only the mints and burns the window saw, and never
self-heals.

Replaying the last 100 blocks of Ethereum's deepest USDC/WETH pool produces a
state whose active liquidity is 5481181047667912297 and whose tick is 197999 —
**both exactly the contract's own, verified against it** — with a tick map
containing nothing at all. §18.7.1's traversal over that map then returned eight
bands, every one `reachable=False`, `reached_bps=0`, zero notional. For the
deepest pool on the chain. [[REQ-WP-059]], merged yesterday, draws that as
"exhausted at 0 bps", which on a chart is a statement about the market.

## §18.7.2's recovery check cannot catch it

It compares the three scalars a swap already reports. On that state two matched
exactly and the third differed by 1.4e-8 relative — under a thousandth of a basis
point of price, drift over the blocks between the last swap and the read. A
reader would call it noise and be right. The tick map is invisible to it because
it never looks there.

**I got that number wrong first.** I wrote 1.4e-14 into the module docstring
after subtracting two 34-digit integers in my head and dropping six orders of
magnitude. The test I then wrote asserted `< 1e-12` and failed, which is how it
surfaced. The conclusion was unchanged; the figure was not, and it is corrected
everywhere it appeared.

## The detection is the pool's own arithmetic

In a concentrated-liquidity pool the liquidity at the current tick is the running
sum of `liquidity_net` over every initialised tick at or below it. So

    sum(liquidity_net for tick <= current_tick) == active_liquidity

holds for a complete map, and the two sides come from **different events** —
mints and burns on the left, the swap's own report on the right. A disagreement
proves incompleteness with no archive node, no checkpoint and nobody's assertion.
Equality does not strictly prove completeness, since errors could cancel, and the
module says so rather than implying otherwise.

Only contiguity still has to be asserted: a block with no `Mint` is
indistinguishable from a block whose `Mint` was not fetched.

## Two existing fixtures described pools that cannot exist

Adding the guard to the traversal broke three tests, and two of them were wrong
rather than inconvenient. `thin` had a million units of active liquidity at tick
0 with its only initialised tick at 30 — liquidity active at spot has to have
been minted at or below spot, so that is not a thin pool, it is an incomplete
map. The no-price fixture had a million units of liquidity and no price at all.

Both now describe pools that could exist and test the same behaviour.

## The sweep found a guard that guarded nothing

`DEPTH_CAPABLE` named the two classes a traversal may run over, and **nothing
read it.** The mutation that widened it to every class survived, because the
traversal checked the invariant directly.

That was not a dead constant; it was a hole. A `GAPPED` reconstruction whose
surviving events happen to balance passes the invariant, so it would have
produced a curve. A `PoolState` carries no provenance, so the traversal cannot
see a gap — the fix is two gates, each where the information it needs exists,
rather than one that would take the other's input on trust.

The sweep also found that no test put a tick exactly at the current tick, so
`<=` and `<` were indistinguishable; and that my gap-ordering test could not
tell the two orderings apart, because a *balanced* gapped map reaches `GAPPED`
either way. The discriminating case is gapped **and** partial, and the state is
labelled by its cause rather than its symptom.

## The contrast with chain 999, measured

The fixture records `contract_agrees_with_last_swap`. On Ethereum the historical
`eth_call` matched the logs exactly; on HyperEVM it does not, which is
[[ADR-067]]. So an `ANCHORED` state is reachable on one chain and not the other,
and that is a property of the endpoints rather than of this code — which is why
the quality is a value on the row instead of a global assumption.

## What this does not deliver

Nothing yet drives the reconstruction from stored `dex_liquidity` rows: it is
invoked with events a caller supplies. The table exists, the quality exists, and
the pipeline that materialises one from the other is the next piece.
