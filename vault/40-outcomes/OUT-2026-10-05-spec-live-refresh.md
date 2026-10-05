---
id: OUT-2026-10-05-spec-live-refresh
step: spec
records: [REQ-WP-090]
commit: null
---

## What was done

Read `vault/10-requirements/REQ-WP-090.md` (no `ACCEPTANCE-NOT-SPECIFIED`), the constitution, and the page code (`App.tsx`
single load, `Chart.tsx` range reset on every data change, `loadId` guard, `LoadState` vocabulary, pinned branch), then
wrote `specs/139-live-refresh/spec.md` with `traces: [REQ-WP-090]`, the checklist, and the vault spec note.

## What was decided

- **Stage 1 only.** The requirement splits the work itself and says stage 2 (worker events through the API hub to the
  page) may become its own requirement; this spec records it as out (FR-009) rather than designing half a WebSocket.
- **Refresh is the same load, on a timer.** No new endpoint, no new query shape: the tick re-runs what open runs, through
  the existing `loadId` supersede guard plus a new in-flight skip.
- **The range reset is the defect inside the defect.** `Chart.tsx` sets the visible range on every data change today, so a
  timer alone would yank pan/zoom every minute; FR-007 lets only the initial load (and timeframe/mode changes) set the
  range.
- **Interval is `VITE_CHART_REFRESH_MS`, default 60 s** (the requirement's own number); a missing/zero/negative/unparseable
  value disables the refresh instead of polling tightly.
- **Failure keeps the picture.** The `failed` vocabulary (role `alert`) states it; the chart never blanks and a failure is
  never drawn as an empty market.

## What is still open

- The push path (stage 2) as its own requirement and spec; the tick stays as its fallback.
- Whether to shorten the producers' 5-minute passes (the requirement says separate; the interval cannot show what the API
  does not yet serve).
- Live screenshots (plan/tasks will place them, following the bar-gaps and volume-profile pattern).
