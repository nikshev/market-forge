---
id: OUT-2026-10-04-plan-chart-candidates-no-data
step: plan
records: [REQ-WP-084]
commit: null
---

## What was decided

- **Three pure functions carry the decisions, the components attach them**: `extremumMarkers` gets a required
  `includeCandidates`; `panes.ts` gets `availablePanes` and `chooseSelection`. The earlier UI work found that a
  component test can never see a drawn mark in jsdom, so the part that can be wrong is the part with direct tests.
- **Candidates are filtered where the no-look-ahead rule already lives.** `extremumMarkers` withholds candidates
  not yet observed at the instant in AS-SEEN-THEN; routing the switch through it means the switch can widen the
  view and cannot look ahead (Principle I), with no second filter to keep in step.
- **`available` is `null` while unknown.** The page has no "series in flight" state, so before the first answer
  every pane looks empty; reading that as "no data" would be the false claim REQ-WP-009 FR-016 forbids. A
  `pointsLoaded` flag is the one new piece of page state it needs.
- **A "no data" pane is a disabled button with its label kept** ("CVD no data"), no `aria-label`, so a pane
  with data keeps exactly its old accessible name and the existing `FlowPane` tests pass unchanged.
- **The selection moves only when the current choice is unavailable.**

## What was rejected

- A `extrema_candidates` deep-link layer: breaks §27.2's vocabulary and its Python mirror, or leaves old links unreadable.
- Remembering the switch in `localStorage`: it would reopen the noisy view the owner complained about.
- Asking `/features/snapshot` or a registry endpoint for availability: one more request, and "ever" or "at one
  instant" instead of "in this view".
- Hiding the "no data" panes: the row would change shape as data arrives and hide what exists.
- A tooltip on a disabled button: needs a wrapper and is not announced.

## What is still open

- On the live stack every pane will read "no data" until a feature producer exists, so the "populated" look
  needs fixtures in the screenshots; the plan's screenshot script serves a stub features response for that.
  Whether a stubbed screenshot is honest enough is recorded in the implement note when it is taken.
- The disabled buttons' contrast in dark mode is for looking at, not for a computed ratio (disabled controls
  are exempt from WCAG's contrast rule, but a reader must still read the label).
