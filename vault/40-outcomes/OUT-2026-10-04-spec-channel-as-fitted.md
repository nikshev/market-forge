---
id: OUT-2026-10-04-spec-channel-as-fitted
step: spec
records: [REQ-WP-082]
commit: null
---

## What was done

Specified [[REQ-WP-082]] after reading `series.ts`, the model's fit, the stored table and the live response, because
the first thing found was the cause: the page repeats the current levels for every bar.

## What was decided

- **The channel is exact from the stored levels and the slope**; the page reconstructs the window rather than
  asking a server for points.
- **The window ends at the snapshot's own bar** (§27.5, as seen then), not at the chart's last bar.
- **No usable slope draws nothing**: an absent channel is not a flat one, a principle `series.ts` already states.

## What is still open

- The channel's history bar by bar (each earlier snapshot) needs a range endpoint and is out of scope.
