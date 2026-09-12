---
id: OUT-2026-09-12-implement-dex-depth-panes
step: implement
records: [REQ-WP-059]
commit: null
---

## What was done

`features/dex.py` (`dex_swap_imbalance`), `DexBands.tsx`, a staleness judgement
in `dexDepth.ts`, the pool in the deep link, and the pane in `panes.ts`. 11
Python tests and 17 web tests, **13 of 13 mutants caught**.

## One pane, not two

§27.3 lists `DEX swap imbalance` and `DEX active liquidity`. Only the first was
buildable, and the reason is the shape this project keeps meeting.

**`notional_usd` is `None` on every swap this system produces.** It is declared
nullable on `DexSwapEvent`, stored as a column by [[REQ-WP-053]], and set by no
producer — the v3 reducer emits token amounts and no USD price. §18A.4's
`signed swap USD flow` would therefore be absent on every swap, and a pane of it
would render "no readings of this feature" forever, which is the message the
application produces honestly for a genuine absence. A reader could not tell it
from a quiet market.

So the imbalance is denominated in token0, which the reducer does produce, and
the registration says so rather than leaving a reader to infer it from a number
that looks like a fraction either way.

`DEX active liquidity` is not offered at all. §18.12.2's `active_liquidity`
lives on a `LiquidityState` nothing reconstructs, which on HyperEVM needs an
archive node no public endpoint provides ([[ADR-067]]).

**The name was already expected.** `research/dex_incremental.py` and
`research/defi_confluence.py` have both looked for features prefixed
`dex_swap_imbalance` since EXP-007 and EXP-015 were written, and found none.
That was not a coincidence I noticed afterwards — it is why the feature is
called that.

## Two tests that were written to fail here, and one that quietly stopped checking

`test_the_dex_panes_are_not_offered_yet` and
`test_every_dex_family_is_empty_in_the_registry_today` both asserted the absence
this requirement fills, and both said in their own docstrings that failing was
the right way to find out. They failed. That is the system working.

**The third one is the interesting one.** EXP-007's ablation is cumulative, so
`plus_swap_imbalance` runs only if every family before it has features too.
Registering `dex_swap_imbalance` changed *why* that arm reports "not run" — from
its own family being empty to the two empty families ahead of it — and the test
asserted only `result is None` and `reason` being truthy. It stayed green across
a change it existed to notice.

It now asserts which absence stopped each arm: that
`plus_swap_imbalance`'s reason no longer names `swap_imbalance`, and does name
the family that actually blocked it.

## The judgement nothing was making

`depthAgeNs` has computed the gap between a curve's instant and the chart's
since [[REQ-WP-054]], and deliberately left the threshold to a caller. **There
was no caller.** An hour-old curve was drawn with exactly the confidence of a
current one.

`depthFreshness` makes the call, with the threshold as an argument so the
boundary itself is tested, and a default of one minute justified by block times
rather than by taste: five Ethereum blocks, sixty HyperEVM ones ([[REQ-WP-052]]
measured both).

**It has four states, not two.** A plain magnitude comparison would call a curve
*later* than the instant it is drawn at "fresh" — a chart showing a reader what
that moment could not have known, which is Constitution Principle I on screen
rather than in a feature. That is `ahead`, and it says so.

## A chain id that is not one

The pool comes from the deep link, because nothing else can name it: a CEX venue
and symbol do not identify an AMM pool, and inferring one would be §17's
cross-venue mapping done by guess.

`parseInt("12abc")` is 12. A chain id read that way would request depth from a
real chain, with real pools, that nobody named — and the response would look
like an answer. The parser takes a positive integer or nothing, and chain and
pool are read together or not at all: either alone produces a request that can
only fail, and then a notice about a layer nobody could have had.

## What this does not change

Every `_ns` field in the web app except `DexDepthResponse`'s two is still a
`number`, quantising to the nearest 256 nanoseconds — [[REQ-WP-054]]'s open
question, unchanged. Nothing added here widens it: the staleness arithmetic is
`bigint` throughout, including the age formatting, which is exactly where
somebody would be tempted to convert. The chart's cursor is still a `number`
and therefore still quantised, and the comparison is accurate to 256ns against
a threshold of a minute — said in the code rather than left for a reader to
discover.
