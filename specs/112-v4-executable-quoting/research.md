# Phase 0 — Research

Everything below was measured this session against Ethereum mainnet, or read out
of code in this repository. Nothing is recalled.

## Where is the quoter, and how do we know it is one?

**Decision**: `V4Quoter` at `0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203`, and the
adapter verifies it rather than trusting the constant.

**Rationale**: a remembered address is not evidence. Two candidate addresses were
probed for code; one had 5820 bytes, the other none. The one with code was then
asked `poolManager()` and answered
`0x000000000004444c5dc75cb358380d2e3de08a90` — the same singleton every
`Initialize` log in `tests/fixtures/uniswap_v4/initialize.jsonl` was emitted
through. `StateView` at `0x7ffe42c4a5deea5b0fec41c94c136cf115597227` answered the
same. That match is the identification, and it is the check the adapter performs
at runtime.

**Alternatives considered**: a per-chain address table. Rejected: it makes the
constant load-bearing, and a wrong entry produces reverts that look like thin
pools.

## What does the quoter's interface look like?

**Decision**:
`quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))`,
selector `0xaa9d21cb` computed from that signature, returning
`(uint256 amountOut, uint256 gasEstimate)`.

**Rationale**: the outer struct holds a `bytes` member so it is dynamic — the
call data opens with an offset of 32, then the five static `PoolKey` words, the
direction, the size, the offset to `hookData` (8 × 32, measured from the start of
the tuple) and its length. This encoding was confirmed by getting real answers
back from three pools; a wrong layout reverts rather than returning a plausible
number, which is why one working call is sufficient evidence of the layout.

**Alternatives considered**: `quoteExactOutputSingle`, multi-hop. Out of scope —
§18.8.1 asks for an executable quote, not a router.

## How does a refusal arrive?

**Decision**: every refusal observed arrives as `UnexpectedRevertBytes(bytes)`
(`0x6190b2b0`) wrapping the real reason. The adapter unwraps one layer and
matches the inner selector.

**Rationale**: measured on all seven refusals in the capture. Two distinct inner
reasons appear, each selector computed from its signature, not copied:

| selector | signature | where |
|---|---|---|
| `0x7a5ed734` | `NotEnoughLiquidity(bytes32)` | `0x5ce617f9…` at all four sizes; `0xf7caa8ee…` in reverse |
| `0x7c9c6e8f` | `PriceLimitAlreadyExceeded(uint160,uint160)` | `0x5d10cbe0…` in reverse |

`NotEnoughLiquidity` carries the pool id, and in every case it equals the pool
asked about — checked, not assumed. `PriceLimitAlreadyExceeded` carries
`(current, limit)`, and in the one observed case both equal
`1461446703485210103287273052203988822378723970341`, which is also that pool's
`slot0` sqrt price and is `MAX_SQRT_PRICE - 1`: the pool sits at the quoter's own
ceiling, so an upward swap is refused before it starts.

**Alternatives considered**: treating any revert as one undifferentiated failure.
Rejected: "this pool has no depth" and "you asked to push the price past the end
of the number line" are different facts, and the second is about the request.

**Unknown selectors** decode to an explicit `UNKNOWN` reason keeping the raw
payload. An unrecognised reason is not a missing one, and must never collapse
into a recognised one.

## Does the existing tick path already refuse these pools?

**Decision**: no, and it cannot. The gate must be on the reconstruction class.

**Rationale**: measured. A `PoolState` built from the fixture's own state record
for `0xf7caa8ee…` passes `require_tick_map_complete` — the tick map is empty and
the pool reports zero liquidity, so the map explains the pool exactly — and
`depth_to_bps(bps=50, upward=True)` then returns `reachable=False, amount0=0,
amount1=0, reason="the pool has no active liquidity, so its price cannot be
moved"` for a pool that absorbs a whole ETH at the same block.

[[REQ-WP-060]]'s guard is not weak here; it answers a different question and
answers it correctly. Nothing inside the tick path has the information to catch
this, because the information is the hook address.

## What is the replay seam?

**Decision**: `ChainDataProvider` (already in `src/channelflow/chain/providers.py`,
PRD §18.17's interface). Replay is a provider that answers `eth_call` from the
fixture.

**Rationale**: this makes Constitution VII literal instead of approximate. One
adapter encodes, one adapter decodes, and the only thing CI substitutes is where
the bytes come from. A second "replay adapter" would leave the encoder untested
offline, which is where an error would be silent — a mis-encoded `int24` produces
a revert or a different pool, and a replay path that skipped encoding would never
see it.

The protocol has no way to convey a revert payload today, so `CallReverted`, with
a `.data` attribute, is added beside `NoHealthyProvider`. There is no concrete
implementation of `ChainDataProvider` in `src/` yet (checked), so nothing breaks.

**Alternatives considered**: a `QuoteSource` protocol with live and replay
implementations. Rejected for the reason above — it puts the seam above the
encoder rather than below it.

**One thing the fixture stores decoded**: the `poolManager()` answer. The capture
verified both contracts name the singleton and recorded the address in the header
rather than the raw 32-byte return. The replay provider serves that header value
for `poolManager()`. It is a recorded fact stored in decoded form, and it is
named here so nobody later mistakes it for an invented one.

## Can a mid be computed?

**Decision**: a mid is the geometric mean of the two directions' implied prices,
taken from two quotes at the same block, and asking for one where either
direction refused raises.

**Rationale**: measured — `0xf7caa8ee…` and `0x5d10cbe0…` each quote ETH→token
and then refuse to buy back the exact amount they had just offered. There is a
price to buy and none to sell. Any mid for those pools would be manufactured
here.

**Alternatives considered**: returning the one-sided price as a mid, or halving
it. Both produce a number that is positive, ordered and believable, which is this
project's recurring failure shape.
