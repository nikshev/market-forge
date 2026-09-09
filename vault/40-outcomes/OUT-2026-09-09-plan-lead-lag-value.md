---
id: OUT-2026-09-09-plan-lead-lag-value
step: plan
records: [REQ-EXP-010]
commit: null
---

## What was done

One module, 8 tasks.

## What was decided

- **Latency delays the fill, not the signal.** The signal exists when it exists;
  the entry is later.
- **Ties keep the first threshold**, which reports that the filter did not
  matter rather than picking the widest that still worked.
- **The import ban is checked over import lines**, as in [[REQ-US-003]] — "lead
  lag" appears in prose.

## What is still open

- Nothing from this step.
