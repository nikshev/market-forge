# Implementation Plan: The stop path as it was generated

**Branch**: `wp-032-stop-path` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

One module, `apps/web/src/stopPath.ts`, and a component that attaches it.

The module takes a position, its recorded proposals, a mode and an instant, and
returns levels, path points and figures. It does **not** take bars. That absence
is the feature: PRD §44A.33's "not recompute a prettier historical trail" is a
promise about intent until the input a recomputation needs is gone, at which
point it is a property of a signature.

## Technical Context

**Language**: TypeScript 5 · **Dependencies**: none new

**Testing**: vitest over the module, including the criterion that cannot be
satisfied by accident — the same position drawn against two different futures —
plus a mutation sweep.

**Constraints**: `AS_SEEN_THEN` is [[REQ-WP-028]]'s mode, reused. Prices stay
strings on the wire and are compared as numbers only where a comparison is what
is being asked for.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead, ever** | The whole feature. A recomputed trail draws stops from anchors confirmed after the instant drawn at. | **Pass**, held by the signature rather than by review. |
| **VI. Every feature is documented** | Reason codes travel to the view rather than being reduced to a shape. | **Pass.** |
| **XIII. Work is incremental** | The view over the shape the engine produces; recording and serving the path is separate. | **Pass**, and named in the spec. |
| **XIV. Everything is traceable** | `// @trace: REQ-WP-032`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
apps/web/src/types.ts                          # + the position and proposal wire shapes
apps/web/src/stopPath.ts                       # NEW: the decision
apps/web/src/StopPath.tsx                      # NEW: the component that attaches it
apps/web/src/__tests__/stopPath.test.ts        # NEW
```

**Structure Decision**: the decision/component split [[REQ-WP-027]] and
[[REQ-WP-028]] already use, for the reason they found: `lightweight-charts`
cannot lay out a container under jsdom, so anything asserted inside a component
is asserted about a zero-height box. Everything worth testing lives in the
module; the component attaches.

## Spec correction made during planning

**FR-009 was wrong as written** and is corrected in the spec rather than
implemented as written. It said risk *and* excursion must be refused over an
empty path. Excursion genuinely needs a path — MFE and MAE are of something
observed. Open risk is not: it is the distance from the position's own current
stop to its own entry, in units of its own accepted initial risk, and it is
knowable whether or not the policy ever ran. Refusing it would have taught the
reader that an unrun policy means unknown risk, which is the opposite of true.
