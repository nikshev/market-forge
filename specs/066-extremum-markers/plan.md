# Implementation Plan: Extrema on the chart

**Branch**: `wp-028-extremum-markers` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Four layers: a table per shape, both repositories, `GET /api/v1/extrema`, and a
marker decision the chart attaches.

**The correctness rule is put where the storage can enforce it.** A confirmed
extremum's event time on the plane is `known_at_ns`, not `extremum_time_ns`, so
a point-in-time read as of `t` cannot return a turn that had not been confirmed
by `t`. PRD §45's Phase 1A acceptance then holds by construction rather than by
every reader remembering — and the turn's own instant travels beside it, because
that is where the marker goes once the row may be returned at all.

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5 · **Dependencies**: none new

**Storage**: two new lakehouse tables.

**Testing**: pytest and vitest with `@trace` markers, plus a mutation sweep across both halves.

**Constraints**: the knowledge filter is `AS-SEEN-THEN`'s only; optional numbers stay distinguishable from zero.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead, ever** | This is that principle rendered on a screen. | **Pass, and it is the point.** |
| **III. History is immutable** | Later bars must not change what a past instant showed. | **Pass**, and asserted rather than assumed. |
| **II. Time is not one thing** | Two instants per turn, both carried end to end. | **Pass.** Collapsing them is the defect. |

No violations.

## Project Structure

```text
src/channelflow/tables/extrema.py           # NEW: two tables, event-timed on knowledge
src/channelflow/api/repositories.py         # Extrema, the protocol, in-memory
src/channelflow/api/lakehouse_repository.py # the plane's own point-in-time read
src/channelflow/api/schemas.py              # ConfirmedExtremumOut, ExtremumCandidateOut
src/channelflow/api/routes.py               # GET /api/v1/extrema
apps/web/src/extrema.ts                     # NEW: the marker decision
apps/web/src/Chart.tsx                      # one setMarkers call
apps/web/src/App.tsx                        # asks as of the instant, or not at all
```

**Structure Decision**: the rule lives in the schema's event time, restated
nowhere. The in-memory repository has to apply it by hand, which is why the
conformance suite asserts both answer alike.
