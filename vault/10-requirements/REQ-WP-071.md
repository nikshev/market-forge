---
id: REQ-WP-071
title: CUSTOM_ACCOUNTING pools are quoted, never curved
type: work-package
prd_ref: "§18.8.1"
prd_lines: "2928-2949"
phase: 4
status: implemented
depends_on: [REQ-WP-047, REQ-WP-060]
tags: []
---

## Requirement

PRD §18.8.1, line 2945, attaches one rule to the class [[REQ-WP-047]] already
assigns:

> `CUSTOM_ACCOUNTING`: do not assume the standard curve; prefer executable
> quoting/simulation adapter.

[[REQ-WP-047]] delivered the first half — it classifies a pool from its hook
address and refuses to answer for the fee. Nothing delivers the second half, so
today a `CUSTOM_ACCOUNTING` pool has no price at all in this system.

### What the standard curve says about these pools, measured

All four `CUSTOM_ACCOUNTING` pools in `tests/fixtures/uniswap_v4/initialize.jsonl`
were read at Ethereum mainnet block **25975796**, through `StateView` at
`0x7ffe42c4a5deea5b0fec41c94c136cf115597227` and quoted through `V4Quoter` at
`0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203`. Neither address is trusted for
being recalled: both were asked `poolManager()`, and both name
`0x000000000004444c5dc75cb358380d2e3de08a90` — the same singleton that emitted
the fixture's `Initialize` logs.

| pool id | manager `liquidity` | manager tick | 0.01 ETH in |
|---|---|---|---|
| `0xf7caa8ee…` | **0** | 207243 | 9761282090570549416434980 out |
| `0x5d10cbe0…` | **0** | 887271 | 6499876850687097483127271 out |
| `0x5ce617f9…` | **0** | 135269 | refuses |
| `0x88249e68…` | 31690866724818211737594 | 204415 | 7465271246970774645442279 out |

Three of the four hold **zero** liquidity in the manager. A tick-map
reconstruction reads that and reports zero depth — that the pool cannot trade at
any size. Two of those three trade anyway, and trade deeply: `0xf7caa8ee…`
absorbs a whole ETH. The liquidity is in the hook, and the manager's tick map
does not know it exists. `0x5d10cbe0…` sits at tick 887271, one below
`MAX_TICK`, which is a parking space rather than a price.

The fourth holds real liquidity, so the class alone does not tell you which
situation you are in. That is the point: nothing short of the quote separates
"the hook holds the book" from "there is genuinely nothing here".

### A refusal is an answer, and the answers are not all the same refusal

Every refusal arrived wrapped in `UnexpectedRevertBytes(bytes)`, and the payload
inside named a distinct reason — each selector computed from its signature, not
copied:

- `0x5ce617f9…` refuses **at every size on the ladder** (0.001 to 1 ETH) with
  `NotEnoughLiquidity(0x5ce617f9…)`, carrying the pool id that failed.
- `0xf7caa8ee…` and `0x5d10cbe0…` quote ETH→token and then **refuse to buy back
  the exact amount they had just offered**. `0xf7caa8ee…` with
  `NotEnoughLiquidity`; `0x5d10cbe0…` with
  `PriceLimitAlreadyExceeded(1461446703485210103287273052203988822378723970341,
  1461446703485210103287273052203988822378723970341)` — its current price is
  `MAX_SQRT_PRICE - 1`, which is also the quoter's own upper limit, so an upward
  swap is refused before it begins. Both arguments are the same number, and that
  number equals the pool's `slot0`.

So on two of these pools a mid price does not exist. There is a price to buy and
no price to sell, and any figure that split the difference would be invented
here rather than measured on the chain. Direction is not a parameter of a quote;
it is part of what the quote answers.

### Why a refusal must not become a number

[[REQ-WP-060]]'s rule applies unchanged: a quote that did not happen is not a
quote of zero, and not a quote of the last size that worked. `NotEnoughLiquidity`
at 0.01 ETH says nothing about 0.001 ETH, and an adapter that silently retried
downward until something succeeded would report a size the caller never asked
about. The size quoted is part of the answer.

## Acceptance

- A `CUSTOM_ACCOUNTING` pool is priced by an executable quote against a quoter
  contract, never by the concentrated-liquidity kernel. Asking the kernel for
  one of these pools raises rather than returning a figure.
- The quoter is identified by the manager it names, not by a hard-coded address
  per chain: a quoter whose `poolManager()` is not the manager the pool was
  routed under is refused before any quote is attempted.
- A quote carries the size it was taken at, the block it was taken at, and the
  direction. A quote is not a price.
- A mid is never synthesised from one side. Where a pool quotes one direction and
  refuses the other — measured on two of these four — it has no mid, and the
  adapter reports that rather than halving a one-sided number.
- A contract-level refusal is a distinct, named outcome that propagates — with
  the pool id the contract named — and is never rendered as zero, as a stale
  quote, or as a quote at a size the caller did not ask for.
- A quoter refusal is distinguished from an endpoint refusal, exactly as
  [[REQ-WP-046]]'s capture machinery distinguishes them: the first is a fact
  about the pool that every endpoint would repeat, the second is a fact about
  the endpoint.
- The three classes that permit tick reconstruction keep it. This changes what
  happens for `CUSTOM_ACCOUNTING` only.
- Replayable: the adapter is exercised in CI against captured quoter responses,
  including the reverting pool, with no network access.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-112-v4-executable-quoting]]
- **Tests:**
    - `tests/unit/dex/test_v4_quoting.py::test_a_broken_endpoint_is_not_a_refusing_pool`
    - `tests/unit/dex/test_v4_quoting.py::test_a_mid_is_exactly_two_calls_at_one_block`
    - `tests/unit/dex/test_v4_quoting.py::test_a_negative_tick_spacing_fills_the_word`
    - `tests/unit/dex/test_v4_quoting.py::test_a_one_sided_pool_has_no_mid[0x5d10cbe0fdcd8b52e0cf64e84d692b124396a1be49d2b77c1665293bcd855ab4]`
    - `tests/unit/dex/test_v4_quoting.py::test_a_one_sided_pool_has_no_mid[0xf7caa8ee16fff4e0cd360f9248c1dde011a28a0de3038845c85b904cda1c9b75]`
    - `tests/unit/dex/test_v4_quoting.py::test_a_payload_that_is_not_a_wrapper_and_a_missing_payload_are_both_unknown`
    - `tests/unit/dex/test_v4_quoting.py::test_a_question_the_chain_was_never_asked_is_not_answered_zero`
    - `tests/unit/dex/test_v4_quoting.py::test_a_quote_of_zero_cannot_be_built`
    - `tests/unit/dex/test_v4_quoting.py::test_a_quote_request_refuses_a_size_that_is_not_a_size`
    - `tests/unit/dex/test_v4_quoting.py::test_a_quoter_naming_another_manager_is_refused_before_it_is_asked_anything`
    - `tests/unit/dex/test_v4_quoting.py::test_a_reason_inside_the_wrong_wrapper_is_not_read`
    - `tests/unit/dex/test_v4_quoting.py::test_a_refusal_is_asked_once_and_never_retried_smaller`
    - `tests/unit/dex/test_v4_quoting.py::test_a_return_too_short_to_hold_a_quote_is_not_decoded[0x000000000000000000000000000000000000000000000000000000000000007b]`
    - `tests/unit/dex/test_v4_quoting.py::test_a_return_too_short_to_hold_a_quote_is_not_decoded[0x]`
    - `tests/unit/dex/test_v4_quoting.py::test_a_revert_payload_the_endpoint_did_not_send_is_still_a_refusal`
    - `tests/unit/dex/test_v4_quoting.py::test_a_verified_quoter_is_one_that_names_our_manager`
    - `tests/unit/dex/test_v4_quoting.py::test_an_unrecognised_selector_is_unknown_and_never_a_recognised_one`
    - `tests/unit/dex/test_v4_quoting.py::test_every_call_names_the_adapters_own_block`
    - `tests/unit/dex/test_v4_quoting.py::test_every_captured_quote_replays_to_its_exact_amount`
    - `tests/unit/dex/test_v4_quoting.py::test_the_adapter_knows_nothing_about_replay`
    - `tests/unit/dex/test_v4_quoting.py::test_the_deep_pool_absorbs_an_ether`
    - `tests/unit/dex/test_v4_quoting.py::test_the_deep_pool_sells_but_will_not_buy_back`
    - `tests/unit/dex/test_v4_quoting.py::test_the_empty_pool_refuses_at_every_rung_and_names_itself`
    - `tests/unit/dex/test_v4_quoting.py::test_the_encoder_sign_extends_tick_spacing_across_a_whole_word`
    - `tests/unit/dex/test_v4_quoting.py::test_the_fixture_holds_one_block_and_every_answer`
    - `tests/unit/dex/test_v4_quoting.py::test_the_gate_passes_the_three_classes_that_permit_reconstruction`
    - `tests/unit/dex/test_v4_quoting.py::test_the_gate_refuses_every_custom_accounting_pool_in_the_fixture`
    - `tests/unit/dex/test_v4_quoting.py::test_the_pinned_pool_refuses_to_be_pushed_past_the_top_of_the_range`
    - `tests/unit/dex/test_v4_quoting.py::test_the_tick_path_calls_a_pool_that_absorbs_an_ether_unmovable`
    - `tests/unit/dex/test_v4_quoting.py::test_the_two_directions_are_not_reciprocal_and_selling_is_the_worse_side`
    - `tests/unit/dex/test_v4_quoting.py::test_the_two_sided_pool_has_a_mid_between_its_two_prices`
    - `tests/unit/dex/test_v4_quoting.py::test_unknown_is_excluded_alongside_custom_accounting`
- **Code:**
    - `src/channelflow/chain/providers.py`
    - `tools/record/v4_quote_capture.py`
- **Outcomes:** [[OUT-2026-09-14-implement-v4-executable-quoting]], [[OUT-2026-09-14-plan-v4-executable-quoting]], [[OUT-2026-09-14-spec-v4-executable-quoting]], [[OUT-2026-09-14-tasks-v4-executable-quoting]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
