---
id: OUT-2026-09-07-plan-ci-full-gate
step: plan
records: [REQ-INFRA-002]
commit: null
---

## What was done

Planned REQ-INFRA-002 and broke it into 12 tasks. Constitution Check passed with
one gap stated openly.

## What was decided

- **The workflow calls the same `make` targets a developer runs.** Nothing in CI
  reimplements a check, so the two gates cannot drift into disagreeing about
  what "green" means.
- **A gap this feature cannot close was stated rather than hidden.** Its own
  acceptance is a workflow run, and no test inside the suite it gates can prove
  the workflow works. The local half is testable; the CI half is verified by
  observing real runs and recording them. The alternative — a test asserting
  that a YAML file parses — would produce a `VERIFIES` edge that proves nothing,
  which is the token gesture this repository keeps removing.

## What is still open

- Whether the fast gate should also check traceability. It cannot today, because
  `make validate` runs the full suite by design and that is the cost being moved.
