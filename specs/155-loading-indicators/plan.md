# Implementation Plan: Loading indicators

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-103]]

## Design decisions, with what was rejected

1. **One component, `Busy`**, a MUI `CircularProgress` with an accessible name; `progressbar`, never `status`. Rejected: per-place ad hoc markup.
2. **The chart stays mounted under its spinner** (`firstLoad = no bars yet and the answer outstanding`), so it draws the moment the
   bars arrive and `onReady` still fires. A reload shows a small mark by the title instead (the chart is on screen and fine).
3. **A pane waits for what it is made of**: Volume for the bars, the others for the series (`pointsLoaded`, default `true` so a caller
   that does not say is not waiting). While waiting it makes no "no data" claim.
4. **A new `connecting` live status**, so the chip is not called "delayed" before anything has failed.
5. **A spinner in `index.html`**, in `#root`, replaced by React's first render: the page was blank before the script loaded.

## Phases

1. Tests (busy, app, pane, profile, chip, hook). 2. Implementation. 3. Gate, commit. 4. Rebuild the web image; check with the data
requests held back.
