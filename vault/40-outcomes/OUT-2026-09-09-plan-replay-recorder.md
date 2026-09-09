---
id: OUT-2026-09-09-plan-replay-recorder
step: plan
records: [REQ-PIPE-001]
commit: null
---

## What was done

One package, one module, two hooks added to the runner. 9 tasks.

## What was decided

- **Observers rather than a return value.** The runner's report is a summary and
  changing it would break every caller; refitting the snapshots outside the loop
  would be a second fitting path that could disagree with the first.
- **The caller's runner is copied.** One that came back carrying sinks would
  write again on its next use, into whatever store the first run happened to
  use.
- **Both recorders buffer**, for the reason [[REQ-TBL-001]]'s bar sink does: a
  commit per bar would make the snapshot chain as long as the series.

## What is still open

- Nothing from this step.
