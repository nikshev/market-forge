---
traces: [REQ-INFRA-012]
status: draft
---

# Feature Specification: A background pass that fails is reported and tried again; it does not end the process

**Feature Branch**: `130-pass-survives`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-INFRA-012]], on [[REQ-WP-073]] and [[REQ-WP-077]].

## Context

The `worker` and the `resample` job are loops: a pass over the stored bars, a sleep, another pass. A
series that fails inside a pass is printed as `FAILED` and skipped. The first read of a pass — the whole
`bars` table, before any series exists — is outside that guard. An exception there leaves `main`, ends
the process, and compose starts it again.

It happened twice on 2026-10-03: `resample` at 01:02 on a `NoSuchSnapshot` race ([[REQ-WP-079]]), and the
`worker` twice at 16:38 on an `OSError` from an HTTP 503 the object store answered under load (load that the
owner's tooling had caused). The causes have nothing in common. The shape does: **a transient fault in a
dependency cost a process, where it should cost one pass.**

### What restarting costs, and why it is still wrong

Compose restarts the container, so each occurrence is small. But a loop that can only recover by being killed
has no way of saying what happened except a traceback nobody reads, discards whatever the process held, and
makes "the worker is up" mean less than it sounds: it is up *again*. The same condition inside a per-series
read is already survivable and visible; the first read should not be the exception.

### What this is not

Not a retry inside the pass (the next pass is the retry, and a pass is cheap against its interval); not a
backoff (a growing delay would hide how long recovery takes); not a change to what a pass does; not
`maintenance` (it already guards each table) nor the ingest daemons (their own reconnect rules, [[REQ-WP-078]]).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A failed pass costs a pass (Priority: P1)

**Independent Test**: a loop whose pass raises once and then succeeds, with an injected sleep.

**Acceptance Scenarios**:

1. **Given** a pass that raises, **When** the job is looping, **Then** the failure is reported with the job's
   name and the exception's type and message, the loop waits its interval, and the next pass runs.
2. **Given** several consecutive failures, **Then** the traceback is printed **once**, at the first, and each
   later failure prints one line saying how many in a row.
3. **Given** a pass that succeeds after failures, **Then** the recovery is reported with how many passes failed.
4. **Given** a later, separate run of failures, **Then** its traceback is printed again.
5. **Given** a loop that never fails, **Then** it says nothing extra.

---

### User Story 2 - What must still stop the process (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `--once`, **When** the pass fails, **Then** it raises and the process exits non-zero, as today:
   there is no next pass, and surviving would turn a failure into a silent success.
2. **Given** `--once` and a successful pass, **Then** it returns zero.
3. **Given** a `KeyboardInterrupt` or a `SystemExit` in a pass, **Then** it propagates: only `Exception` is survived.

---

### User Story 3 - Both jobs use it, and it is shown (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the `worker` and the `resample` mains in loop mode with a pass that fails once, **Then** each
   reports it and runs the next pass.
2. **Given** a worker started against an object store it cannot reach, **Then** it keeps looping and
   reporting, instead of exiting.

### Edge Cases

- A failure at the very first pass of a new process: survived the same way (the first pass is the one that failed twice).
- A failure while *opening the catalog* before the loop: still ends the process; that is start-up, not a pass.
- An exception whose message is huge or multi-line: reported as it is; no truncation is invented here.
- A failure that never clears: a line every interval is the behaviour; alerting on it belongs elsewhere.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In loop mode a pass that raises an `Exception` MUST be reported with the job's name, the type and
  the message, and the loop MUST wait its interval and run the next pass.
- **FR-002**: The traceback MUST be printed once per run of consecutive failures; each further failure of the
  run MUST print one line with the count.
- **FR-003**: The first success after failures MUST report the recovery and the number of failed passes.
- **FR-004**: In `--once` mode a failing pass MUST raise.
- **FR-005**: Only `Exception` is survived; `KeyboardInterrupt` and `SystemExit` MUST propagate.
- **FR-006**: The `worker` and `resample` MUST both run their passes through it, and a loop's output on a
  healthy run MUST be unchanged.
- **FR-007**: The interval after a failure MUST be the interval after a success.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A pass that fails once is followed by a pass that runs, in both jobs, through `main`.
- **SC-002**: Three consecutive failures print one traceback and three failure lines.
- **SC-003**: Against an unreachable object store, a worker started for the test keeps running for at least
  four intervals, reporting each failure (live, with the date).
- **SC-004**: A healthy loop's output is byte-for-byte what it was.

## Assumptions

- A pass is idempotent over unchanged data (the worker's and the resample's own reports say so), so repeating it is safe.
- The interval is configuration already ([[REQ-WP-077]], [[REQ-WP-073]]).
- Compose's restart policy stays as it is: it is the last resort, not the first.
