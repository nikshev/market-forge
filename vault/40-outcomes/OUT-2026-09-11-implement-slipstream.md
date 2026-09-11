---
id: OUT-2026-09-11-implement-slipstream
step: implement
records: [REQ-WP-045]
commit: null
---

## What was done

`tools/record/slipstream_capture.py`, one chain-read fixture of eight live
pools, `dex/slipstream.py` and the `PoolFamily` classifier in `dex/aerodrome.py`.
38 tests, 23 of 23 mutants caught.

This closes [[REQ-WP-045]]: the v2 curves landed first, Slipstream second.
Status moves to `implemented`.

## The fork is the hazard

Slipstream is a Uniswap v3 fork, and the reason PRD §45 says "using shared CL
kernel" is that most of it genuinely is shared. Tick map, active liquidity,
depth traversal — all [[REQ-WP-015]]'s, all already verified, none rebuilt here.

The trap is one level down. **Slipstream's `Swap` event is byte-identical to
Uniswap v3's** — same arguments, same topic hash. A v3 decoder reads every
Slipstream swap correctly. It is wrong about one thing and never says so:

- **The pool key is `(token0, token1, tickSpacing)`, not the fee.** The
  factory's table is not injective — spacings 10, 50 and 100 all default to
  500 pips — so neither value determines the other. In v3 they do, which is
  exactly why a v3 decoder feels entitled to convert between them.
- **The fee is not the pool's.** `CLPool.fee()` forwards to the factory, which
  forwards to a fee module, and the module in force on Base computes
  `min(baseFee + |tick − twAvgTick|·K/1e6, feeCap)` from the pool's own oracle.
  It moves with the price, every block, with **no transaction and no event** to
  subscribe to. There is nothing to cache and nothing to be notified about.
- **It can depend on who is asking** (a discount keyed on `tx.origin`) and on
  whether a swap is the first in its block.

Measured at the pinned block: **seven of eight live pools charge something
other than their spacing's default.** One charges 2000 where the default says
500.

That is the third time this phase that a venue's arithmetic looked like a
neighbour's and was not — after contract sizes read as base units, and a stable
pool priced as constant product. Each time the wrong number is positive,
ordered and believable.

## Ported, not looked up

So the module computes the fee the way the chain does, and the fixture records
every input the contract reads plus the answer it gives. That makes it an
oracle rather than a recording — the same standard the v2 curves are held to —
and the test asserts **equality**, not tolerance. Eight pools, eight exact
matches, including three carrying a live dynamic term.

Three places where a reasonable reading of the contract gives a different
number from the contract:

- **Solidity truncates toward zero; Python floors.** Tick cumulatives are
  routinely negative, so the two differ by one tick on every negative average
  that does not divide evenly — three pips of fee, at a typical scaling factor,
  on a pool that should have had none.
- **A stored zero already means "nothing configured"**, so the module needs a
  sentinel (420) for a deliberate zero fee. Conflating them charges a default
  to a pool that charges nothing. The initial-fee field has the same three-way
  sentinel again.
- **Default scaling and default cap substitute together.** Substituting only
  the scaling would squeeze the module's default through a pool's own tight
  cap that was never meant to apply to it.

## What the sweep found

23 mutations, 22 caught immediately. The survivor was the `int24` cast on the
average tick replaced by the identity — unreachable from a healthy pool, since
a tick is bounded to ±887272 and no real oracle averages outside `int24`.

Kept and tested rather than deleted. **A port that quietly behaves better than
the contract is a port that disagrees with it**, and disagreeing with the
contract is the one thing this module must never do.

## Two smaller findings

- **Three CL factories are live on Base**, not one: the original plus the
  gauge-caps and min-unstake deployments, holding 3621, 2236 and 1424 pools.
  Recognising only the original — the one the fixture reads — would drop a
  third of the venue's CL pools into `UnknownFamily`. Found by reading
  Slipstream's own deployment output rather than assuming the address everyone
  quotes is the only one.
- **The capture tool now keeps a pool of five endpoints, not two.** Free
  endpoints rate-limit a sustained capture, and the first run died two thirds
  of the way through on a 403. Two healthy endpoints are still required for
  every call — the pool degrades, the guarantee does not. It also had to learn
  the difference between an endpoint declining a *method* and a contract
  reverting: the first should cost one endpoint, the second is a fact every
  endpoint would repeat, and treating it as a refusal would burn the whole pool
  on one reverting call.

## What is still open

- **The nine other tests §18.25 requires per adapter** — reorg rollback,
  checkpoint/replay equivalence, gap failure. Those belong to the adapter that
  wraps this arithmetic, where event ordering lives, not to the arithmetic.
- **Whether a fee is re-read per block or per swap.** Per block is the natural
  granularity for depth features and is what the fixture pins. Per swap matters
  only for the initial-fee path, which no pool in the fixture has enabled.
