---
id: OUT-2026-10-04-plan-channel-as-fitted
step: plan
records: [REQ-WP-082]
commit: null
---

## What was done

Planned three small changes in two layers.

## What was decided

- Reconstruct in the page; an endpoint returning points was rejected (the formula is three lines and the page
  would draw what the server computed).
- **An existing test encodes the fault** (`Chart.test.tsx` asserts one equal point per bar). It is replaced by
  tests of the real shape, and the change is recorded, not hidden.
- The default view is three lookbacks, the channel's own scale, rather than a fixed bar count.

## What is still open

- Whether the colours read on a dark theme; the MUI work that follows carries the theme.
