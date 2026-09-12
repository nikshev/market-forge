---
id: OUT-2026-09-12-implement-hyperevm-decoders
step: implement
records: [REQ-WP-058]
commit: null
---

## What was done

`tools/record/hyperevm_capture.py`, a fixture of real chain-999 logs, and
`chain/hyperevm.py` — the first concrete `ProtocolDecoder` in the repository,
two registered DEX families, and §18.11.2's cross-layer transfers. 33 tests,
**28 of 28 mutants caught**.

## Two protocols, one event signature

The two busiest WHYPE/USDC pools on HyperEVM emit the identical topic0

    Swap(address,address,int256,int256,uint160,uint128,int24)

with the identical five-word payload, and they are different protocols:

    0x6c9a33e3…  factory 0xff7b3e8c…  slot0()        fee() = 500, immutable
    0xbe512f58…  factory 0xf77bd082…  globalState()  Fee(uint16) per swap

[[REQ-WP-047]] met this shape in Slipstream, where the *event* differed and the
decoder could tell. Here nothing in the log distinguishes them. The tell is the
factory, and the consequence is the fee: over the captured 900 blocks the
Algebra pool's own `fee()` reads 1069 while its thirty swaps carry 1069, 1070
and 1071. **Twenty-six of the thirty are mispriced by a decoder that asks the
pool** — each by under two tenths of a percent, which is to say by an amount
that survives every sanity check anyone would write.

So the protocol comes from the registry and a fee nobody published is absent.
`HyperEvmSwap.fee` raises rather than returning a default, and the emitted
`ProtocolEvent` omits the key entirely: a field that is not there cannot be read
as a number by a consumer that forgot to check.

## What I got wrong, and what caught it

**The `Fee` log is not at a fixed offset.** The first sample showed it exactly
three log indices before every swap, and I wrote "three log indices before" into
the requirement and the spec as a measured fact. The second, wider capture has
it at 3, 6, 7 and 10. The pairing was already positional — take the last `Fee`
preceding the swap — so no code changed, but two documents claimed a constant
that does not exist, and a later reader would have had every reason to simplify
the rule to match. The mutation `fee pairing assumes a fixed offset of three` is
now in the sweep so the claim cannot come back quietly.

**I re-ran the capture with an unapplied patch.** A `ruff format` run had
reflowed the lines a patch script matched on; the script asserted, wrote
nothing, and the capture then ran from the chain head and overwrote a good
fixture with a different block range. Every number in the ADR, the requirement
and the spec had to be re-derived. The capture now takes `--from-block` and
`--to-block`, so a fixture that needs a new field is re-recorded over the same
blocks and the notes stay true; re-recording the pinned range reproduced 83
swaps, 30 fee logs and 44 transfers exactly, which is also a check that logs are
deterministic across these endpoints.

**A swap can move nothing on one side.** Two of the 83 captured swaps report
`amount1 = 0`. No transfer settles a side that did not move, so the "nearest
preceding transfer" rule reaches back into whatever the pool did *before* the
swap and finds a real, plausible, unrelated number. It is reported as
`ZERO_SIDE` rather than matched, and the count of them is asserted, so the
exclusion cannot grow without a test going red.

## The oracle had to change ([[ADR-067]])

Every chain capture here verifies decodes against the deployed contract. The
public HyperEVM endpoints cannot do that: asked for `slot0()` a few hundred
blocks back they return near-head state, with no error. Three consecutive
blocks answered with one identical price while the `Swap` logs in those blocks
carried three different ones.

**The two-endpoint quorum from [[REQ-WP-046]] is what caught it** — two
endpoints returned different prices for the same historical call and
`EndpointPool.call` refused rather than picking one. A single-endpoint capture
would have recorded a wrong number silently, and the decoder would have been
"verified" against it.

The replacement oracle needs no archive node: a swap's `amount0` and `amount1`
must equal the pool's nearest preceding transfer of each token in the same
transaction. All 164 moving sides reconcile, across both protocols, offline.

## The sweep found five things nothing asserted

None of them was a bug in the module; all five were assertions I had not
written. No test built a settlement that disagreed, so "a mismatch counts as
matched" survived. No captured transfer moves toward HyperEVM, so the direction
was never checked. No test fed the registry a log that was not a swap, though an
Algebra pool emits a `Fee` for every swap and half its logs are exactly that. No
test asked a decoder about a pool of the other family — the guarantee the
requirement is named for. And no captured word lands between 2^254 and 2^255, so
a sign threshold one bit low was invisible.

## What this deliberately does not deliver

**Pool state reconstruction.** §18.12.2's `LiquidityState` needs tick-level
state at a historical block, and no public endpoint on chain 999 serves it. It
stays on Phase 4's `not_delivered` list, now with a named cause.

**The HyperCore→HyperEVM direction has no fixture.** All 44 captured transfers
move toward HyperCore. The branch is exercised by a hand-built log and the test
says in its own docstring that it is definitional rather than measured.
