---
id: OUT-2026-10-04-plan-pass-survives
step: plan
records: [REQ-INFRA-012]
commit: null
---

## What was done

Planned the survival of a failed pass as `specs/130-pass-survives/`, after reading both loops and
`maintenance`.

## What was decided

- **One shared function.** The two loops are identical; two copies of a survival rule are two chances to
  get it wrong. Rejected: guarding inside `run_pass` around the first read (it covers that read and not
  the next one someone adds).
- **The next pass is the retry; the interval is fixed.** No in-pass retry (a second loop inside the first) and
  no backoff (it hides how long recovery takes behind a number that grows).
- **`except Exception`, because the two incidents' causes share nothing** — a snapshot race and an object-store
  503 — so no list of known causes would have covered both.
- **One traceback per run of failures**, one line for each later one, and a recovery line.
- **The sleep is injected** so no test waits.

## What is still open

- The live proof uses an unreachable object-store endpoint on a throwaway worker, so no other service is
  disturbed (tasks).
