---
id: OUT-2026-09-09-plan-repaint-comparison
step: plan
records: [REQ-US-003]
commit: null
---

## What was done

One module, one endpoint, 8 tasks.

## What was decided

- **Its own module, beside `channels.py` rather than inside it.** That module's
  docstring promises its fits cannot see past the requested instant; a hindsight
  path inside it is how such a promise stops being true.
- **The import ban is checked over import lines**, not over the word
  "comparison", which appears in those packages' prose. A check that failed on a
  docstring would be renamed away rather than fixed.
- **Both existing refusals are reused.** A missing snapshot and an unfittable
  history already raise; this module adds one refusal of its own.

## What is still open

- Nothing from this step.
