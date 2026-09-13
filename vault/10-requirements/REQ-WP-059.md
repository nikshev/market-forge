---
id: REQ-WP-059
title: The chart draws the depth Phase 4 has, and names the pane it cannot offer
type: work-package
prd_ref: "§27.2, §27.3, §18A.4"
prd_lines: "4406-4436, 3712-3721"
phase: 4
status: implemented
depends_on: [REQ-WP-054, REQ-WP-053, REQ-WP-030]
tags: []
---

## Requirement

PRD §27.2 lists `DEX liquidity bands` among the chart's toggle layers and §27.3
lists two lower panes:

    - DEX swap imbalance;
    - DEX active liquidity.

[[REQ-WP-054]] serves the bands and `dexDepth.ts` already decides what to draw —
`DRAWN`, `NO_CURVE`, `FAILED`, reached against exhausted, the curve's own
instant. **Nothing draws any of it.** `dex_liquidity_bands` is a declared
overlay name that toggles nothing, and `panes.ts` offers seven of §27.3's nine.

### The overlay

An exhausted band is the reason this layer cannot be a plain series. [[ADR-036]]
separates a band the walk reached from one where the book ran out first, and on
a chart the two are the same shape: drawn alike, an exhausted band reads as a
cheaper market than exists. The decisions are made and tested; drawing them is
what is missing.

The curve also carries its own instant, which is not the cursor's whenever the
most recent curve predates it. `depthAgeNs` computes the gap and **nothing
decides what gap is too much** — so a curve from an hour ago is currently drawn
with the same confidence as one from this second.

### One pane, not two

§18A.4 lists what an AMM offers in place of a bid/ask queue, among it
`directional swap imbalance` and `signed swap USD flow`. Only the first can be
built honestly today.

**`notional_usd` is `None` on every swap this system produces.** It is declared
nullable on `DexSwapEvent`, stored as a column by [[REQ-WP-053]], and no
producer sets it — the v3 reducer emits token amounts and no USD price. A
USD-denominated flow feature would therefore be absent for every swap, and a
pane of it would say "no readings" forever, which is the failure `panes.ts`
already refuses to ship.

The signed token amounts *are* produced, so the imbalance is denominated in
token0:

    imbalance = sum(amount0) / sum(abs(amount0))

over the swaps of a window, where `amount0` is signed from the pool's side.
Bounded in [-1, 1]; -1 is every swap buying token0, +1 every swap selling it.

**A swap can move nothing on one side.** [[REQ-WP-058]] measured two of eighty-
three captured swaps reporting a zero amount. A zero contributes to neither the
numerator nor the denominator and is not a direction.

**A window with no swaps has no imbalance.** Not zero — zero is the reading for a
window that was perfectly balanced, and a pane that drew a flat line through
quiet hours would be claiming balance where there was silence.

**`DEX active liquidity` is not offered.** §18.12.2's `active_liquidity` lives on
`LiquidityState`, which nothing reconstructs; on HyperEVM that needs an archive
node no public endpoint provides ([[ADR-067]]). Offering the pane would put a
phase's unfinished work in front of a reader as though it were finished.

## Acceptance

- The `dex_liquidity_bands` layer draws REQ-WP-054's bands when it is on, and
  nothing when it is off.
- A reached band and an exhausted band are distinguishable without reading the
  numbers, and an exhausted one shows how far the book actually got.
- `FAILED` and `NO_CURVE` produce different notices, and neither is drawn as an
  empty layer (REQ-WP-009's FR-016).
- A curve older than a stated threshold is marked stale, with the age shown; the
  threshold is a tested decision, not a constant inside a component.
- `dex_swap_imbalance` is registered with §19's sixteen fields and computed from
  signed swap amounts; a window with no swaps yields no value, and a swap with a
  zero amount changes neither the numerator nor the denominator.
- `panes.ts` offers the DEX swap imbalance pane, and the registry knows its
  feature (`tests/unit/features/test_pane_features.py`).
- Nothing offers a `DEX active liquidity` pane while nothing reconstructs pool
  state.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-100-dex-depth-panes]]
- **Tests:**
    - `tests/unit/features/test_dex.py::test_a_balanced_window_reads_zero`
    - `tests/unit/features/test_dex.py::test_a_swap_after_the_cursor_is_not_visible`
    - `tests/unit/features/test_dex.py::test_a_swap_that_moved_no_token0_is_counted_but_has_no_direction`
    - `tests/unit/features/test_dex.py::test_a_window_of_only_zero_swaps_has_no_imbalance`
    - `tests/unit/features/test_dex.py::test_a_window_spanning_nothing_is_refused`
    - `tests/unit/features/test_dex.py::test_an_empty_window_has_no_imbalance`
    - `tests/unit/features/test_dex.py::test_no_usd_denominated_swap_feature_is_registered`
    - `tests/unit/features/test_dex.py::test_one_sided_windows_reach_the_bounds`
    - `tests/unit/features/test_dex.py::test_the_feature_is_registered_and_says_what_it_is`
    - `tests/unit/features/test_dex.py::test_the_imbalance_is_the_signed_flow_over_the_gross_flow`
    - `tests/unit/features/test_dex.py::test_the_window_is_half_open_at_the_floor_and_closed_at_the_cursor`
    - `tests/unit/features/test_pane_features.py::test_no_active_liquidity_pane_is_offered`
    - `tests/unit/features/test_pane_features.py::test_the_dex_swap_imbalance_pane_is_offered`
- **Code:**
    - `apps/web/src/DexBands.tsx`
    - `apps/web/src/__tests__/DexBands.test.tsx`
    - `src/channelflow/features/dex.py`
- **Outcomes:** [[OUT-2026-09-12-implement-dex-depth-panes]]
<!-- trace:end -->

## Notes

When this was written, every `_ns` field in the web app except
`DexDepthResponse`'s two was a `number`, quantising to the nearest 256
nanoseconds — [[REQ-WP-054]]'s open question. Nothing added here made it worse:
the staleness arithmetic was `bigint` throughout. **[[REQ-WP-061]] closed it**,
and every instant in the app is now a `bigint` parsed at the API boundary.
