---
id: OUT-2026-10-03-spec-snapshot-single-load
step: spec
records: [REQ-WP-079]
commit: null
---

## What was done

Specified the single-load read as `specs/124-snapshot-single-load/spec.md`, three stories and
eight requirements. The evidence is the deployment's own log from the night of 2026-10-02/03:
`worker` 10 occurrences, `resample` 4 (three caught per series, one fatal at 01:02). Before
writing it, the three operations that ask more than once were read (`read`, `current`,
`snapshot`) and the callers of `current()` were listed: `pipeline/replay.py` (twice),
`lakehouse/research.py`, `models/registry.py`. So the fault is wider than the two processes that
logged it.

## What was decided

- **The fix belongs in the layer that raises the error, not in its callers.** A catch-and-retry
  in the worker and resample would hide the fault and would also hide a snapshot that genuinely
  does not exist; FR-007 forbids it.
- **A read a moment old is acceptable.** After one load the newest snapshot is the newest *of that
  version*; a commit a millisecond later is not seen. That is the answer a reader a millisecond
  earlier would have had, so it is not look-ahead (Principle I).
- **The deterministic test is the proof; the looping reader and writer is evidence.** A race test
  that passes by luck proves nothing, and the spec says so in SC and in the requirement.
- **Resample's uncaught first read is left alone.** It is the same process dying for a different
  reason next time; whether it should survive is a separate decision, recorded as out of scope.

## What is still open

- The count of places that load a table more than once has not been taken beyond the three
  operations named; the plan must audit every `self._table()` / `self._require_table()` site
  before the tasks are written, because the spec's FR-001..003 name only these three.
- `_describe` finds its snapshot with `next(...)` and no default, so a snapshot that vanished
  between a membership check and the describe would be a `StopIteration`, not `NoSuchSnapshot`.
  Whether that can occur once a single load is used is for the plan to settle.
- Whether the real-catalog loop test can be made non-flaky in the fast gate or belongs in the
  integration set.
