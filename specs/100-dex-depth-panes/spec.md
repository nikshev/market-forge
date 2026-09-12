---
traces: [REQ-WP-059]
status: draft
---

# Feature Specification: The chart draws the depth Phase 4 has

**Feature Branch**: `wp-059-dex-depth-panes`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-059 — PRD §27.2's DEX liquidity bands layer and §27.3's DEX
panes.

## Context

`dexDepth.ts` already decides everything about the layer — three states,
reached against exhausted, the curve's own instant — and is tested. No component
consumes it, and `dex_liquidity_bands` is a declared overlay name that toggles
nothing.

§27.3 lists two DEX panes. Only one has data: `notional_usd` is `None` on every
swap this system produces, so a USD flow pane would read "no readings" forever;
`active_liquidity` lives on a `LiquidityState` nothing reconstructs. The
directional imbalance over signed token amounts is producible today.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The bands are on the chart (Priority: P1)

A reader turns on `DEX liquidity bands` and sees the depth curve for the pool:
each side's bands in increasing distance, with the amount each consumes.

**Acceptance**: with the layer on, every band in the response is rendered; with
it off, none is, and no notice is shown either.

### User Story 2 - An exhausted band does not read as a cheap market (Priority: P1)

A pool too thin to move 100 bps returns a band that never reached its target.

**Acceptance**: reached and exhausted bands are distinguishable without reading
the numbers; an exhausted band shows the distance the book actually reached
alongside the target it did not.

### User Story 3 - A stale curve says so (Priority: P1)

The most recent curve predates the cursor by an hour.

**Acceptance**: the overlay is marked stale and the age is shown. The threshold
is a tested function, not a literal inside a component.

### User Story 4 - The pane offered is the pane that has data (Priority: P1)

A reader opens the lower pane selector.

**Acceptance**: `DEX swap imbalance` is offered and draws from registered
feature values; no `DEX active liquidity` pane exists; a window with no swaps
renders the pane's `unavailable` state rather than a line at zero.

### Edge Cases

- A swap with `amount0 = 0` — observed on chain 999 (REQ-WP-058). It is not a
  direction and must not enter the denominator.
- Every swap in a window zero: the denominator is zero and there is no
  imbalance, which is not the same as an imbalance of zero.
- A response with bands but a null `state_time_ns`: drawable, staleness unknown.
- `FAILED` and `NO_CURVE` must not collapse into one blank layer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The layer renders only when `dex_liquidity_bands` is among the
  selected overlays.
- **FR-002**: Bands are grouped by side and ordered by increasing target.
- **FR-003**: An exhausted band carries a distinct role and shows `reachedBps`
  against `targetBps`.
- **FR-004**: `FAILED` and `NO_CURVE` each render their own notice and no bands.
- **FR-005**: Staleness is decided by a function in `dexDepth.ts` taking the
  overlay, the cursor instant and a threshold, all in `bigint`.
- **FR-006**: `dex_swap_imbalance` = `sum(amount0) / sum(abs(amount0))` over a
  window's swaps, `None` when that denominator is zero.
- **FR-007**: The feature is registered with §19's sixteen fields, declares
  `no_lookahead`, and its null policy states the silence rule.
- **FR-008**: `PANES` gains the imbalance pane and no active-liquidity pane.

### Key Entities

- **DepthOverlay** — existing; gains no fields.
- **DepthStaleness** — `fresh` / `stale` / `unknown`, plus the age.
- **SwapImbalance** — the value and the swap count behind it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The overlay renders every band of a real captured response.
- **SC-002**: Toggling the layer off removes every band and every notice.
- **SC-003**: A window of swaps summing to zero signed flow yields an imbalance
  of exactly 0; a window of no swaps yields none.
- **SC-004**: Mutating the denominator, the zero-amount rule, the staleness
  comparison or the pane list is caught by a test.

## Assumptions

- The pool a chart shows is supplied by the caller; discovering which pool
  corresponds to a CEX symbol is §17's cross-venue mapping and out of scope.

## Open Questions

- Every `_ns` field in the web app except `DexDepthResponse`'s two is a
  `number`. Unchanged here, and nothing added widens it.
