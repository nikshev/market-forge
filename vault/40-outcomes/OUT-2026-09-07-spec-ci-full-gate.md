---
id: OUT-2026-09-07-spec-ci-full-gate
step: spec
records: [REQ-INFRA-002]
commit: null
---

## What was done

Specified REQ-INFRA-002 as `specs/003-ci-full-gate/spec.md`. Ten functional
requirements, five success criteria, two user stories both at P1.

## What was decided

- **Both user stories are P1, which is unusual and deliberate.** Normally
  priorities force a choice. Here they cannot be separated: removing checks from
  the local hook without them running somewhere would weaken verification
  silently, which is the failure this whole repository exists to prevent. US1
  without US2 is worse than doing nothing.
- **FR-009 is the load-bearing requirement**: a check removed from the local
  hook must run in the workflow, and none may be dropped from both. Everything
  else is mechanics; this is the constraint that keeps the trade honest.
- **The workflow is authoritative for `implemented` status.** Requirements
  verified only by integration tests now earn that status on a workflow run, not
  a local one. Recorded in the spec's Assumptions as a change in *where*
  verification is established, not a weakening of it.
- **GitHub Actions with job services, not Docker Compose in CI.** The workflow
  runs on Linux where services are provisioned natively; reusing the compose
  file would mean maintaining a second code path for the same two containers.
  Both read the same `.env.example` defaults, so a divergence is a bug in one
  place rather than two.
- **`git ls-remote --exit-code` misled me during investigation.** It returns a
  non-zero code when no refs match, and an empty repository has none — I read
  that as "remote unreachable" and briefly concluded CI was impossible. The
  remote was fine; the repository was simply empty. Corrected before acting on
  it. Noted here because the same flag will mislead the next person.

## What is still open

- **Whether the fast gate should also run traceability coverage.** It cannot
  today: `make validate` runs the full suite by design, and that is the cost
  being moved. A cheaper variant that validates against a committed graph
  snapshot is conceivable but is not specified here.
- **No branch protection is configured.** The workflow will run, but nothing
  requires it to pass before a merge. That is a repository setting, not a file,
  and it is the user's to make.
- **The 64 commits pushed to `nikshev/market-forge` predate this workflow**, so
  the first run covers all of them at once. If it fails, the failure is about
  the workflow's own configuration, not about those commits.
