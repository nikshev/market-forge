---
id: OUT-2026-09-09-plan-setup-families
step: plan
records: [REQ-US-005]
commit: null
---

## What was done

One module, one field on the production machine, 10 tasks.

## What was decided

- **`SignalMachine.opens` defaults to `None`**, meaning every pair. Every caller
  before this feature gets exactly the engine they had, which is what
  [[REQ-WP-010]]'s parity test compares against.
- **`middle_continuation_short` borrows §13.11's middle-zone defaults**, because
  §31 writes out only the upper family. The report carries the numbers, so the
  borrowing is visible rather than assumed.
- **A test asserts the family module contains no engine logic**, by name:
  `CandidateState`, `Transition`, `on_bar`, `rejected(`.

## What is still open

- Nothing from this step.
