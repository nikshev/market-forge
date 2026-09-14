---
id: REQ-WP-071
title: CUSTOM_ACCOUNTING pools are quoted, never curved
type: work-package
prd_ref: "§18.8.1"
prd_lines: "2928-2949"
phase: 4
status: planned
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
- **Code:**
    - `tools/record/v4_quote_capture.py`
- **Outcomes:** [[OUT-2026-09-14-plan-v4-executable-quoting]], [[OUT-2026-09-14-spec-v4-executable-quoting]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
