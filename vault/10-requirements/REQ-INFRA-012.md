---
id: REQ-INFRA-012
title: "A background pass that fails is reported and tried again; it does not end the process"
type: infrastructure
prd_ref: "none -- operational finding, 2026-10-03; repository practice (REQ-WP-079, REQ-WP-081)"
prd_lines: "0-0"
phase: null
status: planned
depends_on: [REQ-WP-073, REQ-WP-077]
tags: [reliability, worker, resample]
hard_gated: false
---

## Requirement

The `worker` (channels, [[REQ-WP-077]]) and the `resample` job ([[REQ-WP-073]]) run as loops: one pass over
the stored bars, a sleep, another pass. Inside a pass each series is guarded, so one series that fails is
printed as `FAILED` and skipped. **The first read of a pass is not**: it reads the whole `bars` table
before any series exists, and an exception there leaves `main`, ends the process, and relies on compose to
start it again.

That has now happened twice, for two unrelated reasons:

| when | process | cause |
|---|---|---|
| 2026-10-03 01:02 UTC | `resample` | `NoSuchSnapshot` on the first read, a race with writers ([[REQ-WP-079]]) |
| 2026-10-03 16:38 UTC | `worker`, twice | `OSError` from an HTTP 503 answered by the object store under load |

Compose restarts the container, so the cost is small each time. It is still the wrong shape: a transient
fault in a dependency should cost one pass, not a process; every restart discards what the process held;
and a loop that can only recover by being killed has no way of saying what happened except a traceback
nobody reads. The same condition in a per-series read is already survivable and visible.

A pass that fails must be **reported** (once per run of failures, with the cause), **survived** (the loop
sleeps and tries the next pass), and its recovery **reported**. In `--once` mode, where there is no next
pass, the failure must still end the process non-zero, as it does today. Anything that is not an
`Exception` — an interrupt, an exit — must still stop the process.

## Acceptance

- A pass that raises, in loop mode, is reported with the job's name and the exception's type and message;
  the loop waits its interval and runs the next pass, which runs.
- A run of consecutive failures prints the **traceback once**, at the first, and one line for each later
  failure: a repeated condition does not repeat its full report ([[REQ-WP-078]]'s rule).
- The first pass after a failure that succeeds reports the recovery and how many passes failed.
- In `--once` mode a failing pass raises and the process exits non-zero.
- `KeyboardInterrupt` and `SystemExit` are not swallowed.
- `worker` and `resample` both use it: a test drives each through `main` with a pass that fails once.
- Shown live: a worker started against an object store that cannot be reached keeps looping, reporting each
  failure, instead of exiting.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-130-pass-survives]]
- **Outcomes:** [[OUT-2026-10-04-plan-pass-survives]], [[OUT-2026-10-04-spec-pass-survives]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Out of scope: `maintenance` (it already guards each table), the ingest daemons (their own reconnect rules,
[[REQ-WP-078]]), and what to do about a failure that never clears: a loud line every interval is the
behaviour, and alerting on it belongs with the observability work.
