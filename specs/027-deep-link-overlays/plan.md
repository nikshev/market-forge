# Implementation Plan: The alert's link restores the chart it was sent about

**Branch**: `us-002-deep-link-overlays` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

PRD §27.2's layer list travels in the alert's link, and the chart opens on the
signal's own bar with exactly those layers drawn — or says it could not restore
them.

## Technical Context

**Language/Version**: Python 3.12 and TypeScript.

**Primary Dependencies**: none new.

**Testing**: pytest for the link, vitest for reading it back and for the range.

**Target Platform**: `src/channelflow/alerting/`, `apps/web/src/`.

**Constraints**: FR-006 extends [[ADR-020]]; FR-008 to FR-010 are pure functions
in `series.ts`, where jsdom's lack of layout cannot reach them.

**Scale/Scope**: one module each side, 6 link tests and 16 web tests.

## Constitution Check

- **VI (every feature is documented)** — the page states which of the three
  restoration states it is in, so a reader is never guessing whether the chart
  matches the alert.
- **XI (results are reproducible)** — one alert produces one link: the overlay
  set is sorted and deduplicated before serialization.
- **XIV** — traces to REQ-US-002.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/alerting/
├── overlays.py   # NEW: PRD 27.2's twelve layers
├── models.py     # + Alert.overlays
└── render.py     # + the &overlays parameter

apps/web/src/
├── overlays.ts   # NEW: reading the list back, and the three states
├── types.ts      # + OVERLAYS, DEFAULT_OVERLAYS
├── series.ts     # + visibleRangeFor
├── deepLink.ts   # + overlays on the parsed link
├── Chart.tsx     # draws only what is on; centres on the instant
└── App.tsx       # states the restoration when it is not exact
```

**Structure Decision**: `visibleRangeFor` lives in `series.ts` for the reason
that file exists — jsdom cannot lay out a container, so a component test would
assert nothing about where the chart looked. The decision is extracted; the
attachment is not tested.

## Approach

**The vocabulary is duplicated deliberately, and the duplication is named.**
`Overlay` in Python and `OVERLAYS` in TypeScript are the same twelve strings.
The alert writes them and the chart reads them, so the pair is a wire contract;
a comment on each side says so, because a rename on one side would silently drop
a layer.

**A partly-readable list is discarded whole.** [[ADR-020]] falls back to the safe
view when the channel mode is mangled. An overlay list can be partly readable,
which is worse: a restored subset looks restored while missing whichever layer
the reader most needed. So the fallback is all-or-nothing, and it is stated.

**An empty list is a statement, not an absence.** `overlays=` means no layers
were on; falling back to defaults there would overrule a recorded fact with a
guess.

**The chart is stubbed in the page test.** `lightweight-charts` cannot
initialize in jsdom; the tests assert what the reader is told, which sits above
the chart rather than inside it.

## Complexity Tracking

> No violations.
