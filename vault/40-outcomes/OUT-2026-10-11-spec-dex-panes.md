---
id: OUT-2026-10-11-spec-dex-panes
step: spec
records: [REQ-WP-099]
commit: null
---

## What was done

Specified and planned [[REQ-WP-099]] (spec 151) in one step: the owner chose to give the two DEX panes a source. The spec,
plan and tasks are in `specs/151-dex-panes/`.

## What was measured first

- The public HyperEVM node allows `eth_getLogs` over 1000 blocks at most and **rate limits inside a 200 response** (`-32005`)
  after a handful of calls in a second; each log carries `blockTimestamp`.
- The two pools produce about 43 swaps per 500 one-second blocks, so quiet minutes are normal.
- Both pools are WHYPE (18) / USDC (6); one is Uniswap v3 (fee 500, spacing 10), one Algebra Integral (spacing 5).

## What was decided

- **Pinned pools, no discovery**; **one `eth_getLogs` per piece for both pools**; **coverage from the poll's own `dex_state` row**;
  **active liquidity from the busiest pool**; **Bybit `HYPEUSDT` as the carrying series**. Each with what it rejects, in the plan.

## What is still open

- Whether a second HYPE market should carry the panes (each series costs a worker cycle); whether other chains' pools are wanted.
