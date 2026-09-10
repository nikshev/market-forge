---
id: OUT-2026-09-10-implement-stop-path
step: implement
records: [REQ-WP-032]
commit: null
---

## What was done

`apps/web/src/stopPath.ts` (the decision), `apps/web/src/PositionView.tsx` (the
attachment), the §44A wire shapes in `types.ts`, and
`tests/unit/stops/test_view_contract.py` (the seam between the two languages).

25 web tests and 6 Python ones. Every gate clean: 1662 Python, 98 web, build
included. 16 of 16 mutants caught in the view after the sweep, 3 of 3 in the
contract check.

RED first: `stopPath.test.ts` collected zero tests and failed to resolve
`../stopPath`, which is the honest red for a module that does not exist yet.

## What the sweep found

Four survivors, and one of them was a test of mine that had stopped testing.

- **A reason the view had never heard of.** The test invented
  `HELD_SOMETHING_ADDED_LATER`, and a mutant that filtered reasons down to a
  known list survived it — because the invented code still *looked* familiar
  enough to pass the filter. The test now uses a code sharing no prefix with
  anything this build knows. A test written to prove unknown things survive,
  which quietly only proved familiar things survive, is the exact shape of the
  failure the requirement is about.
- **The instant itself.** `at_ns <= atNs` versus `<`. The boundary falls the
  inclusive way — a decision made at `atNs` was knowable at `atNs` — and
  excluding it hides the most recent stop update on every chart drawn at the
  moment it happens, which is every live chart. No test covered it.
- **Arrival order.** Nothing promises a stored path arrives sorted. Drawn in
  arrival order the staircase steps backwards through time and reads as a stop
  that moved down and then up — the one shape §44A.2's monotonic rule forbids.
- **A failure line that always renders.** The test asserted a real failure
  appears and never that an absent one does not, so a mutant showing the load
  error permanently survived. The view now has to be quiet when nothing failed.

## What was decided while building

- **The component is `PositionView.tsx`, not `StopPath.tsx`.** A component file
  differing from `stopPath.ts` only in case resolves to the module on a
  case-insensitive filesystem, and the import comes back `undefined` with a
  React error naming the wrong cause. The rest of the app already avoids this
  (`FlowPane.tsx` / `panes.ts`); this follows it, and §44A.33's own words
  ("Position page/chart") name it better anyway.
- **The line is a staircase, not a glide.** A stop holds its price until a
  decision moves it. Interpolating between two proposals draws it sitting at
  prices it never sat at — the prettier trail §44A.33 forbids, reintroduced by
  a drawing choice rather than by a computation. It has its own test.
- **The Python check earns R2 honestly rather than formally.** A TypeScript-only
  requirement cannot satisfy a rule that reads pytest markers, and the tempting
  answer is a token test. The real gap is a schema drift nobody owns: a field
  added to `StopProposal` and not to the view produces no error and no gap — the
  view keeps drawing a decision, correctly, missing the part someone added
  because a reader needed it. The check also refuses to let `refused` be a
  rendering branch with no reason code behind it.

## What is still open

- **Nothing stores stop proposals, and no endpoint serves them.** The view is
  built over the shape the engine produces, as the derivatives panes were built
  over features nothing writes. `PositionView` is not yet wired into `App.tsx`
  for that reason: a page with no data source would be a blank panel presented
  as a feature.
- **Trail aggressiveness and data-health status**, two of §44A.33's fifteen
  fields, have no producer. Named in the spec's Open Questions.
- **The "why moved / why not tighter" grouping** is not built. The reason codes
  reach the view and are listed; splitting them into the PRD's two headings
  needs a mapping that arguably belongs nearer the policy that emits them.
