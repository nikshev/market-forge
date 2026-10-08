---
id: OUT-2026-10-08-tasks-notarize-final-records
step: tasks
records: [REQ-INFRA-007]
commit: null
---

## What was done

Broke [[REQ-INFRA-007]] into 42 tasks in `specs/143-notarize-final-records/tasks.md`, in nine phases: measurements
that decide a margin; the pure core (hash, RFC 9162 tree, records, context); registration in the pass; batching,
submission and the outbox; the chain client and signer; verification, export, latency and the claim; the service
and deployment wiring (ending in the `tested` commit); the live steps; close-out. Tests precede the code they
exercise; the pure core also gets mutation specs in `tests/mutations/`, because that is how this repository audits
acceptance (`make mutate`). The live phase is last and starts only from a clean, committed tree, because the
image bakes in the commit and a dirty tree makes every record unnotarizable by design.

## What was decided

The cross-artifact analysis found no constitution conflict and every FR and SC mapped to a task. It found five
inconsistencies, fixed in the artifacts rather than carried:

1. **Two documents each assumed the other held the pass-time bound.** The spec said "a bound stated in the
   plan"; the plan said "measured in the tasks". The plan now states it: **110 % of the baseline pass time**,
   including with the chain unreachable.
2. **A setting appeared in the tasks and nowhere else.** The gas margin (which depends on whether Monad charges
   the limit or gas used, task T002) is now in the quickstart's configuration list.
3. **SC-001 says eight hash tests; the tasks specified four.** Four inputs × two kinds (snapshot, decision). The
   task now says eight.
4. **Non-final records were both "refused" (FR-004) and "stored as unnotarizable" (data model).** They are
   refused: counted, logged as an error, never registered. A leaking record is a bug to surface, not a row to
   keep. Unnotarizable is reserved for a missing commit, a dirty tree or an unhashable config.
5. **The context's config hash had no stated source.** It must come from the runner the pass actually used, built
   once per pass; the wiring task now says so.

Looked at and left: the `suppression` kind has no live producer (the worker delivers no alerts); its schema and
tests exist and `docs/notary.md` is to say so rather than imply coverage. Three tasks (T001, T034, T042) map to no
FR; they are measurement and commit steps.

## What is still open

- **The mutation CLI's exact invocation** for a single spec file is checked when T012 runs; the repository's
  `make mutate` runs all of them.
- **Live-phase risk:** T036 rebuilds `worker` and starts `notary` on the running stack. Nothing is measuring the
  worker's start time now (REQ-WP-079's window closed on 2026-10-04), `--no-deps` limits it to those two
  services, and the pass-time check follows immediately. It is still a change to the running deployment and is
  done last, after everything else is green and committed.
- **The faucet balance (4.92 MON) is a shared constraint** with [[REQ-INFRA-009]] (resolve transactions) and the
  smoke runs; T040 records the observed cost per day so the next requirement can plan against a number.
- **The `signal_transitions` defect** (candidates frozen at first sight) is not addressed by any task here; it is
  reported in the plan outcome and needs the user's decision.
