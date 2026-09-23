---
id: OUT-2026-09-23-spec-chart-timeframe-control
step: spec
records: [REQ-WP-074]
commit: null
---

## What was done

[[REQ-WP-074]] specified as `specs/119-chart-timeframe-control/spec.md`.
`traces: [REQ-WP-074]`; requirement note visible as
[[SPEC-119-chart-timeframe-control]].

The requirement was re-extracted on 2026-09-17 from a narrow "the deep link's
timeframe reaches the read" into the whole mechanism: control, link and address
are one thing, and specifying one without the others is how the state and the
screen came apart in the first place.

## What was decided

**The offered set is a read of its own, and this is where the API surface is
settled.** [[REQ-WP-073]]'s FR-002 deferred the frontend's half explicitly: "§28
lists no endpoint carrying the set". The spec makes it FR-002 here — a read
reporting each token and its `timeframe_ns` — with the shape (path, schema) left
to planning. The alternative, a constant in the frontend, is the second list
that requirement exists to prevent.

**`1m` is offered although `CHANNELFLOW_TIMEFRAMES` never names it.** §5.1 lists
`1m` among Phase 1's timeframes and the ingest daemon always produces it; the
variable names what *resampling* builds. An offered set that omitted the one
series guaranteed to exist would be wrong in the most visible way. Recorded as
an assumption with the reasoning, because the configuration alone does not imply
it.

**The default is `15m`, in one place.** It is `parseDeepLink`'s current default,
and the spec keeps it rather than inventing a new one. If a deployment
configures it away, it is refused like any other unhonourable token — not
silently swapped for a neighbour, which would be the same class of defect the
feature exists to remove.

**Refusal beats fallback, visibly, with the token named.** "An unsupported `tf`
falls back to the default with a notice" was considered and rejected: the chart
would still be drawn, at a timeframe nobody asked for, and the notice competes
with the chart for meaning. No request is issued at a substituted timeframe.

**The address is updated, not the navigation.** A timeframe change writes the
query so a copy reproduces the view, and the mode control's half is in scope
because it is the same mechanism — `apps/web/src/App.tsx` has no
`replaceState` at all today, so the mode control changes the screen and not the
link.

**A stale response must not overwrite a newer choice.** Changing timeframe twice
quickly is a real reader action, and the last selection is the answer. Stated as
FR-012 because it is observable and cheap to get wrong.

**Presentation is not settled.** Styling and component library stay out,
per the requirement's Reference section; the planning step may choose, and the
choice can be revised without reopening this spec.

## What is still open

- **The route's shape.** `/api/v1/timeframes` and its response schema are a
  planning decision; the spec fixes only that the read exists and what it means.
- **Where the API processes read the variable.** `CHANNELFLOW_TIMEFRAMES` must
  reach the API as well as the resampler from a single value in `.env`; the
  compose wiring is planning's, not the spec's.
- **Whether the frontend bundle size justifies anything.** The control is small;
  no performance question was found worth stating as a criterion.
