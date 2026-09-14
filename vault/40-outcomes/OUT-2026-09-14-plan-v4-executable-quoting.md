---
id: OUT-2026-09-14-plan-v4-executable-quoting
step: plan
records: [REQ-WP-071]
commit: null
---

## What was done

Planned [[REQ-WP-071]] into `specs/112-v4-executable-quoting/` — plan, research,
data model, one contract and a quickstart.

## What was decided

**The replay seam is the RPC provider, not the adapter.** CI runs the one real
quoting path against a `ChainDataProvider` that answers `eth_call` from
`tests/fixtures/uniswap_v4/quotes.jsonl`. So the call encoder, the ABI decoder
and the revert unwrapping are all exercised offline. The rejected alternative —
a `QuoteSource` protocol with separate live and replay implementations — puts
the seam *above* the encoder, and a mis-encoded `int24` tick spacing is exactly
the error that would then never be seen in CI. `CallReverted`, carrying the
revert payload, is added to the existing protocol; there is no concrete
implementation of it in `src/` yet, so nothing breaks.

**The gate is on the reconstruction class, because nothing downstream can see
this.** Measured while planning: a `PoolState` built from the fixture's own state
record for pool `0xf7caa8ee…` **passes** [[REQ-WP-060]]'s
`require_tick_map_complete` — an empty tick map explains a pool reporting zero
liquidity perfectly — and `depth_to_bps` then returns `reachable=False,
amount0=0` with the reason "the pool has no active liquidity, so its price cannot
be moved", for a pool that absorbs a whole ETH at that block. That guard is not
weak; it answers a different question correctly. The only place the information
exists is the hook address, so the gate goes there.

**`CURVE_RECONSTRUCTIBLE` is a permit list.** `UNKNOWN` is excluded alongside
`CUSTOM_ACCOUNTING` — §18.8.1 gives it "raw data only; exclude from predictive
depth features", the same prohibition reached by a different route. A class added
later is excluded until somebody decides otherwise.

**A mid is the geometric mean of two same-block quotes, or it is an exception.**
Halving a one-sided price, or passing it off as a mid, produces a number that is
positive, ordered and believable — this project's recurring failure shape.

**Scope held to exact-input, single-hop, empty hook data.** Exact-output and
multi-hop are a router, which §18.8.1 does not ask for.

## What is still open

**The gate has no chokepoint yet, only a door.** Nothing in this repository
currently bridges a v4 pool into `PoolState`, so `require_curve_applies` cannot
be forgotten by existing code — only by code written later. The plan covers this
with a test that asserts the wrong answer `depth_to_bps` gives when the gate is
bypassed, so the hazard is visible rather than implied. If a v4→`PoolState`
bridge is ever built, the gate belongs inside it, and this note is the reason.

**`poolManager()` is replayed from a decoded header value.** The capture verified
both contracts name the singleton and recorded the address, not the raw 32-byte
return. That is a recorded fact stored decoded — named here so nobody later reads
it as an invented one.

**One block only.** Whether the two one-sided pools stay one-sided is a fact
about launchpad hooks, not about this adapter, and a second capture would be the
way to find out.
