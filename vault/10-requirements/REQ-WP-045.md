---
id: REQ-WP-045
title: The Aerodrome family prices each pool by its own invariant
type: work-package
prd_ref: "§18.10, §18.24, §18.25, §45 Phase 4"
prd_lines: "3038-3088, 3549-3600, 6811"
phase: 4
status: implemented
depends_on: [REQ-WP-015]
tags: []
---

## Requirement

PRD §45's Phase 4 lists "Aerodrome Slipstream and v2 adapters" and §18.10 says
why one adapter is not enough:

    Aerodrome currently exposes more than one AMM shape, so one decoder is
    insufficient.

    At minimum model:

        AERODROME_V2_VOLATILE
        AERODROME_V2_STABLE
        SLIPSTREAM_CL
        FUTURE_AERO/METADEX_ADAPTER

and, for v2, states the rule this requirement exists to enforce:

    Depth is calculated from the correct pool invariant, not from CL ticks.

**Three curves, one venue.** A volatile v2 pool is constant product. A stable v2
pool uses the Solidly invariant `x³y + y³x = k`, which is a different curve with
a different depth profile at the same reserves. Slipstream is concentrated
liquidity and reuses the kernel [[REQ-WP-015]] already built.

**Pricing a stable pool with the constant-product formula produces a plausible
number that is wrong**, and nothing downstream shows a symptom — the same shape
of failure as reading OKX's contract sizes as base units ([[REQ-WP-044]]), and
the reason §18.10 states the rule explicitly rather than leaving it to be
inferred.

**The pool says which it is.** Solidly-family pools expose `stable()`; a pool
that does not answer it is constant product. The classification is therefore
read from the chain, not guessed from a name or a token pair — a USDC/USDT pool
can be either.

**The contract is the oracle.** §18.25 requires every adapter's "quote curve
matches contract view within tolerance", and an Aerodrome v2 pool exposes
`getAmountOut(amountIn, tokenIn)` — its own answer to the question this adapter
computes. Verification is against that, not against a fixture somebody wrote.
Base's public RPC answers without a key and two independent endpoints agree on
the head block, so there is nothing between this repository and the authority.

## Acceptance

- A pool's curve is read from the chain (`stable()`), never inferred.
- A quote from the volatile invariant matches the pool's own `getAmountOut`
  within tolerance, at a real pool and a named block.
- A quote from the stable invariant matches the pool's own `getAmountOut` within
  tolerance, at a real pool and a named block.
- The two invariants disagree measurably on the same reserves, asserted — so a
  test cannot pass while silently using one for both.
- Depth for a v2 pool is computed from its invariant and never from ticks.
- A pool whose curve cannot be established is refused, not assumed volatile.
- Slipstream reuses [[REQ-WP-015]]'s concentrated-liquidity primitives rather
  than a second copy of them, and its protocol metadata stays separate (§18.10.2).
- The fixtures are chain reads at pinned blocks, captured by a committed tool,
  and no test opens a socket.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-083-aerodrome-v2]], [[SPEC-084-slipstream-fees]]
- **Tests:**
    - `tests/unit/dex/test_aerodrome.py::test_a_pool_with_an_empty_side_cannot_quote`
    - `tests/unit/dex/test_aerodrome.py::test_a_swap_of_nothing_is_refused`
    - `tests/unit/dex/test_aerodrome.py::test_a_volatile_pool_conserves_the_product`
    - `tests/unit/dex/test_aerodrome.py::test_every_quote_matches_the_pool_s_own_answer_exactly[v2_stable]`
    - `tests/unit/dex/test_aerodrome.py::test_every_quote_matches_the_pool_s_own_answer_exactly[v2_volatile]`
    - `tests/unit/dex/test_aerodrome.py::test_the_fee_is_taken_before_the_invariant`
    - `tests/unit/dex/test_aerodrome.py::test_the_fixture_is_pinned_to_one_block[v2_stable]`
    - `tests/unit/dex/test_aerodrome.py::test_the_fixture_is_pinned_to_one_block[v2_volatile]`
    - `tests/unit/dex/test_aerodrome.py::test_the_invariants_disagree_on_the_same_reserves`
    - `tests/unit/dex/test_aerodrome.py::test_the_iteration_refuses_rather_than_approximating`
    - `tests/unit/dex/test_aerodrome.py::test_the_iteration_terminates_on_the_integer_lattice[490871645057-740882240092-73778518209-18-6-33693336889]`
    - `tests/unit/dex/test_aerodrome.py::test_the_iteration_terminates_on_the_integer_lattice[62632598597-557957931388-922121677-6-18-23865990001]`
    - `tests/unit/dex/test_aerodrome.py::test_the_quotes_span_orders_of_magnitude[v2_stable]`
    - `tests/unit/dex/test_aerodrome.py::test_the_quotes_span_orders_of_magnitude[v2_volatile]`
    - `tests/unit/dex/test_aerodrome.py::test_the_two_directions_are_different_quotes[v2_stable]`
    - `tests/unit/dex/test_aerodrome.py::test_the_two_directions_are_different_quotes[v2_volatile]`
    - `tests/unit/dex/test_slipstream.py::test_a_deliberate_zero_fee_is_not_an_unconfigured_one`
    - `tests/unit/dex/test_slipstream.py::test_a_negative_average_tick_still_contributes_its_distance`
    - `tests/unit/dex/test_slipstream.py::test_a_pool_state_refuses_to_be_built_without_an_observed_fee`
    - `tests/unit/dex/test_slipstream.py::test_a_reverting_observe_charges_no_dynamic_term`
    - `tests/unit/dex/test_slipstream.py::test_all_three_slipstream_factories_are_recognised`
    - `tests/unit/dex/test_slipstream.py::test_an_average_tick_beyond_int24_wraps_as_the_contract_casts_it`
    - `tests/unit/dex/test_slipstream.py::test_an_oracle_too_short_to_answer_charges_no_dynamic_term`
    - `tests/unit/dex/test_slipstream.py::test_every_captured_pool_classifies_as_slipstream`
    - `tests/unit/dex/test_slipstream.py::test_scaling_and_cap_are_substituted_together_or_not_at_all`
    - `tests/unit/dex/test_slipstream.py::test_some_pools_carry_a_live_dynamic_term`
    - `tests/unit/dex/test_slipstream.py::test_the_average_tick_truncates_toward_zero_as_solidity_does`
    - `tests/unit/dex/test_slipstream.py::test_the_cap_binds_after_the_dynamic_term_and_not_before`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0x47ca96ea]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0x4e829f8a]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0x861a2922]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0x98c7a233]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0xafb62448]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0xb2cc224c]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0xdc7ead70]`
    - `tests/unit/dex/test_slipstream.py::test_the_computed_fee_is_the_fee_the_chain_charges[0xf8d5df4d]`
    - `tests/unit/dex/test_slipstream.py::test_the_curve_comes_from_the_factory_and_never_from_a_guess`
    - `tests/unit/dex/test_slipstream.py::test_the_default_table_refuses_a_spacing_the_factory_does_not_enable`
    - `tests/unit/dex/test_slipstream.py::test_the_discount_rounds_in_the_payer_s_favour`
    - `tests/unit/dex/test_slipstream.py::test_the_first_swap_of_a_block_can_be_charged_differently`
    - `tests/unit/dex/test_slipstream.py::test_the_fixture_is_one_block`
    - `tests/unit/dex/test_slipstream.py::test_the_initial_fee_has_its_own_three_way_sentinel[0-500]`
    - `tests/unit/dex/test_slipstream.py::test_the_initial_fee_has_its_own_three_way_sentinel[100-100]`
    - `tests/unit/dex/test_slipstream.py::test_the_initial_fee_has_its_own_three_way_sentinel[420-0]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0x47ca96ea]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0x4e829f8a]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0x861a2922]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0x98c7a233]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0xafb62448]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0xb2cc224c]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0xdc7ead70]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_and_the_factory_agree_about_the_fee[0xf8d5df4d]`
    - `tests/unit/dex/test_slipstream.py::test_the_pool_key_is_the_spacing_not_the_fee`
    - `tests/unit/dex/test_slipstream.py::test_the_spacing_default_is_not_what_pools_charge`
    - `tests/unit/dex/test_slipstream.py::test_the_spacing_table_maps_several_spacings_to_one_fee`
- **Code:**
    - `src/channelflow/dex/aerodrome.py`
    - `src/channelflow/dex/slipstream.py`
    - `tools/record/aerodrome_capture.py`
    - `tools/record/slipstream_capture.py`
- **Outcomes:** [[OUT-2026-09-11-implement-aerodrome-v2]], [[OUT-2026-09-11-implement-slipstream]], [[OUT-2026-09-11-requirement-aerodrome]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

**Where the parts come from, and what is missing.** `nikshev/copy-trade`
(Apache-2.0, same owner) carries a bit-exact Uniswap V3 swap-math port verified
against QuoterV2, constant-product v2 pricing, and the `stable()` probe that
classifies Solidly pools — but **not** the stable-curve quote maths; it detects
those pools rather than pricing them. The invariant therefore comes from
Aerodrome's own published contracts, and the verification from the deployed
pool's own view function.

§18.25's other nine required tests — reorg rollback, checkpoint/replay
equivalence, gap failure, and the rest — are this requirement's too and are the
reason it is larger than a connector.

**FUTURE_AERO/METADEX is out of scope** by §18.10.3's own instruction: a new
deployment gets a new adapter version, and writing one for a contract that does
not exist would bake today's assumptions into the normalized layer.
