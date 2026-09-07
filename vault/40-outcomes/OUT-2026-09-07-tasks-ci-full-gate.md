---
id: OUT-2026-09-07-tasks-ci-full-gate
step: tasks
records: [REQ-INFRA-002]
commit: null
---

## What was done

12 tasks across four phases: mark the integration tests, build the fast gate,
build the workflow, close the loop.

## What was decided

- **T011 and T012 require observing real runs**, not inspecting configuration.
  Both earned their place: T011's observation found that MinIO cannot be a job
  service, and T012's found nothing wrong but proved the negative case works.
- **T009 says "record the comparison, do not assert it"** for FR-009. Comparing
  the two gate lists by hand and writing down the result is stronger than a test
  that could pass while both lists were wrong together.

## What is still open

- Nothing from this step.
