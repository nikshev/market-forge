# Implementation Plan: The chart hides candidate extrema until asked; a pane with no data says so

**Branch**: `133-chart-candidates-no-data` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

Frontend only; no API, no Python change. Three small pure functions carry the decisions and the components
only attach them:

1. `extremumMarkers` takes `includeCandidates`; `Chart` takes `showCandidates` (default `false`); a new
   `CandidateSwitch` (a Material `ToggleButton`, `aria-pressed`) owns the page's boolean.
2. `availablePanes(points)` in `panes.ts`: the set of pane features for which `paneSeries` is `ok`. `FlowPane`
   gets an optional `available` set; a pane outside it is a disabled button reading "no data".
3. `chooseSelection(current, available)` in `panes.ts`: keeps a valid choice, else the first pane with data,
   else `null`. `App` applies it when the availability changes.

## What planning measured

- **`extremumMarkers`** (`extrema.ts`) already filters candidates by `observed_at_ns <= atNs` in AS-SEEN-THEN
  and drops those superseded by a shown confirmation. The switch must go through it, so the no-look-ahead
  filter stays the only place that decides what a candidate is visible at.
- **`paneSeries`** (`panes.ts`) has three states (`ok`, `empty`, `unavailable`); `ok` means at least one point
  carries the feature. That is the spec's definition of "has data".
- **`App.tsx` has no "series in flight" state**: `points` starts `[]`, so before the first answer every pane
  looks `empty`. Labelling that "no data" would be the false claim FR-006 forbids, so a flag
  (`pointsLoaded`) is added: false when a load starts, true when the series answer (ok or failed) arrives.
- **Existing tests that touch panes**: `FlowPane.test.tsx` (renders `FlowPane` directly with points and no
  `available` prop, finds `CVD` and `OFI (1m)` by exact name). With `available` optional and absent meaning
  "all pressable", they pass unchanged.
- **`OVERLAYS`** is §27.2's vocabulary (`tests/unit/alerting/test_deep_link_overlays.py` rejects any other
  name); it is not touched.
- Today the features table has no producer, so on the live chart every pane will read "no data". That is the
  truth the owner asked to be shown, and the screenshots will show it; a populated row needs fixtures.

## Decisions, and what each rejected

**D1. The switch is page state, off on load, not in the link.** Rejected: a new `extrema_candidates` layer
(breaks §27.2's vocabulary and the Python mirror, or makes old links unreadable); `localStorage` (remembering
"on" would reopen the noisy view the owner complained about).

**D2. Filter candidates inside `extremumMarkers`**, with `includeCandidates` defaulting to `true`: the function
describes what is *available* at the instant, and its 13 existing test call sites (11 in `extrema.test.ts`, 2 in
`time.test.ts`) assert behaviour that must not change. `Chart`, the only production caller, always passes the
switch explicitly, and a test fails if it forgets (T004). Rejected: a required parameter (13 edits to tests that
are the regression contract; found by `speckit-analyze`, which caught this plan contradicting its own tasks);
filtering in `Chart` after the call (the pure function would not be the thing under test).

**D3. Availability from the loaded points, by `paneSeries`.** Rejected: asking `/features/snapshot` (one more
request per page, and its answer is for one instant, not the visible range); a list of "built" features in the
page (the thing the pane list's own comment warns against: a second list that drifts from the registry).

**D4. `available` is `null` while unknown.** `null` (loading or failed) shows every pane as today and labels
none "no data"; a `Set` is a decision. Rejected: an empty set for "unknown" (it would read as nine "no data"
during every load).

**D5. A disabled `ToggleButton` with "no data" in its label**, not a hidden button, not a tooltip. Hidden
panes would let the row change shape as data arrives and hide what exists; MUI's tooltip on a disabled button
needs a wrapper and reads nothing to a screen reader. The name stays "CVD" + "no data": the reader learns
what is missing.
`aria-label` is **not** set, so the accessible name is the visible text ("CVD no data"): a pane with data keeps
exactly its old name (FR-009).

**D6. Selection moves only when the current choice is not available.** Rejected: always selecting the first
available pane after each load (it would override a reader's valid choice on every timeframe change).

## Tests (written first)

vitest: `extremumMarkers` with `includeCandidates` false/true (three confirmed + four candidates → 3 / 7, the
same three; AS-SEEN-THEN still withholds a later candidate with the switch on; a candidate superseded by a shown
confirmation stays dropped); `availablePanes` (only `ofi_1m` carried → one; empty series → none; zero value is
data; unknown feature name ignored); `chooseSelection` (valid kept, first available chosen, none → `null`,
unknown availability keeps the choice); `FlowPane` (some panes "no data" are disabled and say so; a pane with
data keeps its name and `aria-pressed`; `available=null` and absent leave every pane pressable; selection
`null` shows "No pane has data for this view" in a `status`); `CandidateSwitch` (named, `aria-pressed`,
calls back); `Chart` with the library mocked as in `chartSeriesCleanup.test.tsx` (default draws no candidate
mark; `showCandidates` draws them; the markers set changes with the prop).

Python (links the requirement to the graph, per [[REQ-WP-083]]'s precedent): the spec's screenshots exist and the
new modules carry their `@trace`. That the pane list names registered features is already pinned by
`tests/unit/features/test_pane_features.py` and is not repeated.

## Constitution Check

I (no look-ahead): the switch widens what is drawn from what the API returned for the chosen instant, through
the existing filter; it never asks for later data. VII: no live/replay difference (display only). XIII:
incremental, one small slice. XIV: traced. IX, X: nothing executes, no new threshold. The rest do not apply:
no new feature, no model, no stored result. **No violations.**

## Risks

- A disabled button's text changes the accessible name for panes without data; no existing test queries those
  by name (checked: only `FlowPane.test.tsx`, with points present).
- The `pointsLoaded` flag must reset when a new load starts, or a stale "no data" would show while loading;
  covered by a test that renders a loading state.

## Project Structure

```text
apps/web/src/extrema.ts            extremumMarkers(includeCandidates)
apps/web/src/Chart.tsx             showCandidates prop (default false)
apps/web/src/CandidateSwitch.tsx   new
apps/web/src/panes.ts              availablePanes, chooseSelection
apps/web/src/FlowPane.tsx          available, "no data", null selection
apps/web/src/App.tsx               the switch state, pointsLoaded, selection
specs/133-chart-candidates-no-data/screenshots.mjs   new, extends the 132 script
tests/unit/web/test_chart_candidates_artifacts.py     new
```
