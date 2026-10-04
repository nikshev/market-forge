---
id: OUT-2026-10-04-implement-chart-candidates-no-data
step: implement
records: [REQ-WP-084]
commit: a64530d
---

## What was done

Candidate extrema are off until the "Candidate extrema" switch is pressed, and a lower pane with no data in the
loaded view reads "no data" and cannot be pressed. Frontend only; no API or Python change.

- `extremumMarkers` takes `includeCandidates` (default `true`); `Chart` takes `showCandidates` (default
  `false`) and always passes it; `CandidateSwitch` is a Material toggle with `aria-pressed`; the switch is
  page state, off on every load, and not in the deep link.
- `panes.ts`: `availablePanes(points)` (by `paneSeries`, the one definition of "has data") and
  `chooseSelection(current, available)`. `FlowPane` takes `available` (a set, or `null` = not known) and a
  `null` selection; `App` adds `pointsLoaded` so a load in flight or a failed one never reads as "no data".

**RED first.** Six new test files (34 tests) were written against unchanged source:

    Test Files  6 failed (6)
    Tests  21 failed | 13 passed (34)
    Error: Failed to resolve import "../CandidateSwitch" from src/__tests__/candidateSwitch.test.tsx
    AssertionError: expected [ ...7 marks ] to have a length of 3        (candidates still drawn when excluded)
    AssertionError: expected [ ...3 marks ] to have a length of 1        (Chart drew candidates by default)
    Unable to find role="button" and name `/no data$/`                   (no pane said it)

The 13 that passed were the ones asserting what already held (an old default, a pane keeping its name, no
"no data" claim for an unknown state). **After:** web 377/377 (340 before + 37), `make lint`, `make typecheck`,
`make web-typecheck` clean, `make web-build` green.

**Bundle gzip:** 163,597 B -> 163,887 B (+290 B).

## Edits to existing tests

- **None to the 340 web tests.** `extremumMarkers` defaulting to `true` is why: its 13 call sites keep
  their meaning. The new cases were added as new files (`paneAvailability.test.ts`,
  `flowPaneAvailability.test.tsx`) rather than appended to `panes.test.ts` and `FlowPane.test.tsx`, which
  are untouched.
- **One Python test of mine narrowed.** `tests/unit/web/test_material_ui_artifacts.py` (REQ-WP-083)
  asserted that `docs/ui/` held exactly its eight PNGs. This requirement's screenshots, taken while the
  commit hook was running, broke it, and it would have broken on every later requirement with images. It now
  checks only files named in its own scheme (page-scheme-width). The hook failing was the test working; the
  fault was the test's scope and my taking screenshots into a shared directory mid-run.

## What looking at the eight screenshots showed

1. **The default chart is clean, and on this chart that means no arrows at all**: the view has no confirmed
   extrema, only candidates, so the owner will see none until the switch is pressed (14 or so grey "?" then
   appear, in both schemes). That is the requirement doing what it says, and it is worth knowing.
2. **On the live stack every pane reads "no data"** and the region below says "No pane has data for this
   view": true today because the features table has no writer.
3. **The populated row is a stub.** `chart-panes-some-data-*` has playwright answer the features request with
   a `cvd` and `ofi_1m` series; it shows what a populated row looks like, **not live data**. The live row is
   `chart-panes-live-no-data-*`.
4. The page opens on the first pane with data (CVD in the stubbed shot), not on a dead one.
5. Disabled "no data" labels are low-contrast in dark mode but legible; disabled controls are exempt from the
   contrast rule and the label still names the pane.
6. The row scrolls inside itself at the right edge ("DEX swap imbal..." cut), as before.

## What was decided

- `includeCandidates` defaults to `true` in the pure function (found by the analysis at the tasks step); the
  chart's test pins that it never relies on that default.
- A pane with data is byte-for-byte the old button; only a pane known to be empty changes.
- Noise in one old test (`chartTimeframeControl`: `Cannot read properties of undefined (reading 'length')`)
  is not new: that test answers every URL with `{bars}`, so the feature series has no `points`, and the old
  `FlowPane` read `points.length` the same way. Left alone.

## What is still open

- The data itself. CVD is computable from the trades ingest already normalises (nothing feeds the feature
  code; `/features/snapshot` returns `{}`); OFI and depth imbalance need a book subscription; OI, funding,
  basis, liquidations need derivatives feeds; the DEX panes need DEX ingest. And **volume, which PRD §27.3 lists
  first, is not a pane at all** ([[REQ-WP-085]], drafted: bars already carry it).
- The "this alert did not record which layers were on" notice shows on any chart opened without an alert; it
  is wrong there. A separate requirement.
