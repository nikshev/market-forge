---
id: REQ-WP-058
title: A HyperEVM pool is decoded as the protocol it is, and a cross-layer transfer as the amount HyperCore credits
type: work-package
prd_ref: "§18.11.2, §18.6"
prd_lines: "3121-3133, 2815-2836"
phase: 4
status: implemented
depends_on: [REQ-WP-014, REQ-WP-052]
tags: []
---

## Requirement

PRD §18.11.2 lists what a HyperEVM adapter tracks, and ends with the sentence
that decides this work:

    A HyperEVM AMM is analyzed according to **its AMM protocol**, not according
    to the Hyperliquid CLOB model.

[[REQ-WP-014]] built the decoder registry §18.6 specifies and [[REQ-WP-052]]
profiled the chain, and no decoder was ever registered — this is the first
concrete `ProtocolDecoder` in the repository. Two of §18.11.2's five tracked
items are still unbuilt: "protocol-specific pool events for DEXs deployed on
HyperEVM" and "HyperCore↔HyperEVM transfer events". Both fail the same way when
guessed, which is why they are one requirement.

### The event signature does not name the protocol

Measured on chain 999 on 2026-09-12. The two busiest WHYPE/USDC pools emit the
identical topic0

    Swap(address,address,int256,int256,uint160,uint128,int24)
    0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

with the identical five-word payload, and they are different protocols:

    0x6c9a33e3…  factory 0xff7b3e8c…  slot0()        fee() = 500, immutable
    0xbe512f58…  factory 0xf77bd082…  globalState()  fee set per swap by a plugin

The second is Algebra Integral: six-field `globalState`, a `plugin()` address,
tick spacing 5 with a fee of 1069 — a combination no Uniswap v3 factory can
produce. Its fee is published per swap as a separate `Fee(uint16)` log, earlier
in the same transaction. **Not at a fixed offset:** across the 30 captured
Algebra swaps the gap to the swap's log index is 3, 6, 7 or 10, so the pairing
is positional or it is wrong.

**This is the same failure [[REQ-WP-047]] met with Slipstream, one step worse.**
There the event differed. Here it is byte-identical, so a decoder keyed on the
signature decodes both and is wrong about one. Over the 900 blocks captured, the
pool's own `fee()` reads 1069 while its thirty swaps carry 1069, 1070 and 1071
— twenty-six of the thirty are mispriced by a decoder that asks the pool, each
by under two tenths of a percent, in the direction of a plausible number.

**So the fee is absent rather than assumed when the log that carries it is not
present.** Absent is not zero and is not the pool's current fee.

### A cross-layer transfer is not the amount it says

A HyperCore↔HyperEVM transfer is an ordinary ERC-20 `Transfer` whose
counterparty is a system address `0x2000…0000 + index`, holding no code. The
low bits are the HyperCore spot index — confirmed for all 44 captured
transfers against `spotMeta`, which also gives each token an
`evm_extra_wei_decimals`. Across the 170 spot assets with an EVM contract it
ranges from −2 to +13:

    USDC   weiDecimals 8    extra −2    EVM decimals 6
    PURR   weiDecimals 5    extra +13   EVM decimals 18

The amount in the log is in EVM units. The amount HyperCore credits is that
divided by `10^extra`. Reading the log's number as the credited number is wrong
by up to ten trillion and is a positive balance either way.

## Acceptance

- A registered decoder produces a swap for both a Uniswap v3-style pool and an
  Algebra Integral pool on chain 999, from real captured logs.
- Protocol is decided by the pool's registry entry, never by the event
  signature: a record from an unregistered address decodes to no event and a
  stated reason, per §18.6's fail-closed rule.
- An Algebra swap decoded without its `Fee` log carries no fee — not zero, and
  not the pool's `fee()`.
- An Algebra swap paired with the `Fee` log of its own transaction carries that
  log's fee, and a transaction holding more than one swap pairs each with the
  fee published for it.
- Every moving side of every captured swap equals the pool's nearest preceding
  transfer of that token in the same transaction ([[ADR-067]]). A side that
  moved nothing has no transfer and is reported as unverifiable, never as
  matched.
- A system address resolves to its HyperCore spot index, and an address that is
  not a system address resolves to nothing rather than to index zero.
- A transfer amount converts to HyperCore units using the asset's
  `evm_extra_wei_decimals`, with any remainder below HyperCore's resolution
  reported rather than discarded silently.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-099-hyperevm-decoders]]
- **Tests:**
    - `tests/unit/chain/test_hyperevm.py::test_a_changed_abi_fails_closed`
    - `tests/unit/chain/test_hyperevm.py::test_a_decoder_refuses_a_pool_of_another_family`
    - `tests/unit/chain/test_hyperevm.py::test_a_disagreeing_transfer_is_a_mismatch`
    - `tests/unit/chain/test_hyperevm.py::test_a_dynamic_fee_pool_cannot_hold_a_pool_level_fee`
    - `tests/unit/chain/test_hyperevm.py::test_a_foreign_token_at_a_system_address_is_not_a_cross_layer_transfer`
    - `tests/unit/chain/test_hyperevm.py::test_a_payload_of_the_wrong_width_is_refused`
    - `tests/unit/chain/test_hyperevm.py::test_a_swap_with_no_preceding_fee_log_is_left_unpriced`
    - `tests/unit/chain/test_hyperevm.py::test_a_system_address_resolves_to_its_core_index`
    - `tests/unit/chain/test_hyperevm.py::test_a_transfer_out_of_a_system_address_moves_toward_hyperevm`
    - `tests/unit/chain/test_hyperevm.py::test_a_uniswap_swap_carries_the_pools_immutable_fee`
    - `tests/unit/chain/test_hyperevm.py::test_an_algebra_event_carries_no_fee_field`
    - `tests/unit/chain/test_hyperevm.py::test_an_algebra_swap_alone_has_no_fee`
    - `tests/unit/chain/test_hyperevm.py::test_an_immutable_fee_pool_must_record_its_fee`
    - `tests/unit/chain/test_hyperevm.py::test_an_ordinary_transfer_is_not_a_cross_layer_transfer`
    - `tests/unit/chain/test_hyperevm.py::test_an_unmeasured_factory_is_refused`
    - `tests/unit/chain/test_hyperevm.py::test_an_unregistered_pool_decodes_to_nothing`
    - `tests/unit/chain/test_hyperevm.py::test_both_families_emit_one_topic`
    - `tests/unit/chain/test_hyperevm.py::test_dust_below_hypercore_resolution_is_reported_not_dropped`
    - `tests/unit/chain/test_hyperevm.py::test_every_algebra_swap_pairs_with_its_published_fee`
    - `tests/unit/chain/test_hyperevm.py::test_every_captured_transfer_converted_exactly`
    - `tests/unit/chain/test_hyperevm.py::test_every_captured_transfer_resolves_to_the_asset_hypercore_names`
    - `tests/unit/chain/test_hyperevm.py::test_every_moving_side_agrees_with_the_transfer_that_settled_it`
    - `tests/unit/chain/test_hyperevm.py::test_family_comes_from_the_factory`
    - `tests/unit/chain/test_hyperevm.py::test_index_zero_is_an_asset_and_not_an_absence`
    - `tests/unit/chain/test_hyperevm.py::test_netting_the_whole_transaction_would_not_agree`
    - `tests/unit/chain/test_hyperevm.py::test_the_credited_amount_uses_the_assets_own_exponent`
    - `tests/unit/chain/test_hyperevm.py::test_the_fee_log_is_not_at_a_fixed_offset`
    - `tests/unit/chain/test_hyperevm.py::test_the_pools_own_fee_misprices_most_of_its_swaps`
    - `tests/unit/chain/test_hyperevm.py::test_the_registry_attributes_each_swap_to_its_own_protocol`
    - `tests/unit/chain/test_hyperevm.py::test_the_registry_declines_a_log_that_is_not_a_swap`
    - `tests/unit/chain/test_hyperevm.py::test_the_sign_bit_is_the_top_bit`
    - `tests/unit/chain/test_hyperevm.py::test_the_tick_is_sign_extended_across_a_full_word`
    - `tests/unit/chain/test_hyperevm.py::test_two_swaps_in_one_transaction_take_their_own_fees`
- **Code:**
    - `src/channelflow/chain/hyperevm.py`
    - `tools/record/hyperevm_capture.py`
- **Outcomes:** [[OUT-2026-09-12-implement-hyperevm-decoders]]
<!-- trace:end -->

## Notes

The capture verifies nothing against historical contract state, because on this
chain it cannot: the public endpoints are not archive nodes and answer a
historical call with near-head state. [[ADR-067]] records that and the
log-only oracle that replaces it.

Two things this deliberately does not deliver. **Pool state reconstruction**
(§18.12.2's `LiquidityState`) needs tick-level state at a historical block,
which no public endpoint on chain 999 will serve; it stays on Phase 4's
`not_delivered` list. **The HyperCore→HyperEVM direction** was not observed:
all 44 captured transfers move toward HyperCore. The address test is symmetric
and handles both, but only one direction has a fixture behind it, and that is
stated rather than implied.
