---
id: OUT-2026-09-09-plan-lookback-sensitivity
step: plan
records: [REQ-EXP-002]
commit: null
---

## What was done

One module, 7 tasks.

## What was decided

- **`find_plateau` and `recommend` are public and separate from the sweep.** The
  sweep takes seconds and the rule takes microseconds; separating them means the
  rule — which is the whole experiment — is tested on constructed sweeps where a
  value sits exactly where the test needs it.
- **The centre of the plateau, not its edge.**
- **A run of one is not a plateau.**

## What is still open

- Nothing from this step.
