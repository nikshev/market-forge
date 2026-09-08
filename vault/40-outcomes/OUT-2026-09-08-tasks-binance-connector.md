---
id: OUT-2026-09-08-tasks-binance-connector
step: tasks
records: [REQ-WP-003]
commit: null
---

## What was done

13 tasks in four phases, grouped by the spec's three user stories.

## What was decided

- **T012 asks for proof that no test touches the network**, by grep and by
  running with the stack down — not by trusting that the design intended it.
- **Liquidation normalization is absent from the task list by decision.** The
  stream carrying it is unreachable from this network, so there is no fixture.
  Writing the code anyway would produce an untested path claiming to work.

## What is still open

- Nothing from this step.
