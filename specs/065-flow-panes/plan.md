# Implementation Plan: Selectable lower panes for order flow

**Branch**: `wp-027-flow-panes` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`panes.ts` decides what a pane draws; `FlowPane.tsx` attaches it; `api.ts` gains
`fetchFeatureSeries`; `App.tsx` loads the window the chart is already showing.

The split follows what this application already does and writes down:
`lightweight-charts` needs a laid-out container, jsdom does not provide one, and
a component test can never see a line. So the part that can be wrong — which
points, which gaps, which refusal — is a pure function with a test file, and the
component is a selector, an SVG and three messages.

## Technical Context

**Language**: TypeScript 5, React 18, vitest · **Dependencies**: none new

**Testing**: `panes.test.ts` for the decision, `FlowPane.test.tsx` for what a reader sees, plus a mutation sweep over the decision module.

**Constraints**: a missing value is a gap; a zero is a zero; three empty-ish states stay apart.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VI. Every feature is documented** | A pane names the registered feature it draws. | **Pass.** |
| **XII. Correctness precedes performance** | An SVG polyline over a few hundred points. | **Pass.** Nothing here is a rendering problem yet. |
| **XIV. Everything is traceable** | Both new modules carry the marker. | **Pass.** |

No violations. Nothing here reads market data or computes a feature, so
Principle I does not arise.

## Project Structure

```text
apps/web/src/panes.ts                    # NEW: PANES, paneSeries
apps/web/src/FlowPane.tsx                # NEW: the selector, the line, the messages
apps/web/src/api.ts                      # + fetchFeatureSeries
apps/web/src/types.ts                    # + FeaturePointOut, FeatureSeriesResponse
apps/web/src/App.tsx                     # loads the series, holds the selection
apps/web/src/__tests__/panes.test.ts     # NEW
apps/web/src/__tests__/FlowPane.test.tsx # NEW
```

**Structure Decision**: the decision module mirrors `series.ts`, which exists for
exactly this reason and says so in its own header.
