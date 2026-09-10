# Phase 1 — Data model

No entities. One wire type mirrored, one value, one state.

## `FeaturePointOut`

`at_ns` and `values: Record<string, number>`. Mirrors PRD §28's shape. **A
feature absent from `values` is silent, not zero** — the whole of what `panes.ts`
exists to draw correctly.

## `PaneSeries`

| Field | Meaning |
|---|---|
| `points` | what to draw, ordered by instant, gaps omitted |
| `state` | `ok`, `empty` (no points at all) or `unavailable` (points, none carrying this feature) |
| `note` | what to say when there is nothing to draw; empty when there is |

`points` is empty in both non-`ok` states, so nothing can be drawn by accident
from a state that means there is nothing.
