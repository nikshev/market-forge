---
id: OUT-2026-09-09-plan-scored-markets
step: plan
records: [REQ-US-001, REQ-US-004]
commit: null
---

## What was done

One new module each side — `api/ranking.py` and `apps/web/src/Explanation.tsx` —
plus the repository, schema and route changes they need. 10 tasks.

## What was decided

- **The ordering left the handler.** It began inline and grew three lookups
  deep; `channels.py` already sets the precedent that anything with a rule in it
  lives where a test can reach it without a client.
- **The panel renders the six groups from a constant, not from the response.**
  A panel that renders whatever arrived cannot show an absence — the absent
  group is exactly the one the response does not mention.
- **`MarketOut`'s three score fields are nullable with no default of zero**, so
  the distinction survives serialization.

## What is still open

- Nothing from this step.
