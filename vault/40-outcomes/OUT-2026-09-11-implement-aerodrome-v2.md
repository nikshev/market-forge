---
id: OUT-2026-09-11-implement-aerodrome-v2
step: implement
records: [REQ-WP-045]
commit: null
---

## What was done

`tools/record/aerodrome_capture.py`, two chain-read fixtures, and
`dex/aerodrome.py` — the two v2 invariants ported from Aerodrome's published
`Pool.sol`. 16 tests, 16 of 16 mutants caught after the sweep.

[[REQ-WP-045]] stays `planned`: this is the v2 half. Slipstream reuses
[[REQ-WP-015]]'s kernel and is the smaller one, done second on purpose so the
requirement's substance was proven before the easy part was dressed up.

## The fixture is not a recording

Every exchange connector this session captured traffic as *evidence about a
format*. Here the pool exposes `getAmountOut(amountIn, tokenIn)` — the
contract's own answer to precisely what this module computes. The fixture is the
authority's number.

That let the test ask for **exact equality** where §18.25 asks only for
agreement "within tolerance". Every intermediate in `Pool.sol` is `uint256`, so
a faithful port agrees bit for bit — and a tolerance would have passed a port
that rounded the wrong way at every step and drifted with trade size, which is
the error a depth curve carries invisibly.

Eight quotes across two real pools, four decades of size each. All exact.

## What the sweep found, and it was worth the search

Twelve mutants died immediately. Three survived, all inside the Newton-Raphson
search that the stable curve needs:

- the derivative losing its factor of three;
- the iteration returning its last estimate instead of refusing;
- the `dy == 0` branches removed entirely.

All three survived for one reason: **the two real pools converge cleanly and
never touch those paths.** The branches exist in the contract because real pools
sometimes do reach them — a nearly-drained stable pool, a trade large against
its reserves.

So the inputs were found by searching the input space: four thousand synthetic
stable pools, looking for one that makes Newton's step round to zero and one
that cannot settle in the contract's 255-step budget. Both exist, both are now
fixtures, and all three mutants are caught.

The derivative one is the most interesting. A wrong `_d` only changes the step
size, so Newton still converges to the same root — on the recorded pools the
answer was identical and no assertion could tell. It is only distinguishable
where convergence is marginal, which is exactly where the searched inputs live.

## Smaller decisions

- **`eth-hash[pycryptodome]` joins the dependencies.** A selector or a log topic
  is the Keccak-256 of a signature, and `hashlib.sha3_256` is SHA-3 — a
  different padding and a different function, which produces plausible wrong
  hashes rather than an error. The capture tool computes its selectors from
  signatures read out of `Pool.sol` rather than copying them, so a typo becomes
  a failed call instead of a wrong one.
- **The capture tool asks two independent RPC endpoints and refuses if they
  disagree.** PRD §18.17 wants a multi-RPC strategy; the reason showed up
  immediately, in that a value both agree on is a value.
- **It also backs off on 429.** These are public nodes nobody pays for.

## What is still open

- **Slipstream**, the other half of [[REQ-WP-045]].
- **The nine other tests §18.25 requires per adapter** — reorg rollback,
  checkpoint/replay equivalence, gap failure. Those belong to the adapter that
  wraps this maths, where event ordering lives.
- **Fixture refresh.** A pinned block is reproducible forever and describes a
  pool that has since moved. Nothing needs a refresh yet.
