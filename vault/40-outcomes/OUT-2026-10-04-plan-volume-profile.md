---
id: OUT-2026-10-04-plan-volume-profile
step: plan
records: [REQ-WP-089]
commit: null
---

## What was decided

- Four phases, the first (collection) deployed as soon as it passes so the data accumulates while the rest is built.
- A separate pure `PriceBinBuilder` (its windows and watermark mirror the bar builder's; the bar builder's tests are untouched); rows carry their bin width.
- `profile.from_bins` reuses the POC and value-area tail of `build`, so the two cannot disagree.

## What was rejected

- Bins on `Bar` (a schema change to the central table), precomputed snapshots, a geometric grid, price lines carrying the width in their titles, a DOM overlay.

## What is still open

- The bins table is read whole per request like the others; revisit if it is slow.
