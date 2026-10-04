# Implementation Plan: A background pass that fails is reported and tried again

**Branch**: `130-pass-survives` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

One small module, `channelflow.pipeline.passes.run_passes(name, one_pass, *, interval_seconds, sleep=None)`,
owns the loop; `channel_main` and `resample_main` replace their two identical `while True` blocks with a call
to it. Failures of a pass are reported, survived and their recovery reported; `--once` and non-`Exception`
exits are untouched.

## What planning measured

- **The two loops are identical** (`while True: run_pass(...); if interval is None: return 0; print; sleep`),
  differing only in what a pass is. Two copies of a survival rule would be two chances to get it wrong.
- **`maintenance` already guards each table** and is not changed.
- **The guarded part of a pass is the per-series loop;** the unguarded part is everything before it, which is
  where both incidents happened: the first read of the whole `bars` table.
- **The incidents' causes differ** (a snapshot race fixed by [[REQ-WP-079]]; an HTTP 503 under load) and no
  list of causes to catch would have covered both, which is why the rule is "any `Exception`", not a list.
- **Output of a healthy loop must not change:** `-- next pass in Ns` is printed after every pass today and is
  kept exactly.

## Decisions, and what each rejected

**D1. One shared function, not a try/except pasted into two mains.** Rejected: pasting (two copies);
guarding inside `run_pass` around the first read (it would cover that read and not the next one added).

**D2. The next pass is the retry.** Rejected: a retry inside the pass (a second loop); a backoff (hides how
long recovery takes behind a growing number); a restart policy in compose (already the last resort).

**D3. `except Exception`.** Rejected: `BaseException` (an interrupt must stop the process); a list of known
causes (there were two and they share nothing).

**D4. One traceback per run of failures.** The first failure prints the exception and its traceback, later
ones one line with the count, the first success the recovery. Rejected: a traceback every time (a dozen for an
hour's outage); no traceback (the first failure of a new kind is the one that needs it).

**D5. `--once` raises.** With no next pass, surviving would be a silent success.

**D6. The sleep is injected,** `sleep=None` meaning `time.sleep` looked up at call time, so a test patches
`time.sleep` or passes a recorder and no test waits.

## Tests (written first)

`tests/unit/pipeline/test_passes.py`: the nine behaviours of the spec through `run_passes` (a failing pass
followed by a pass that runs; one traceback per run and one line per failure with the count; the recovery
line; a second run printing its traceback again; a healthy loop saying nothing extra; `--once` raising and
returning zero; an interrupt and an exit propagating) and both mains in loop mode with a pass that fails once,
and in `--once` mode failing loudly. A mutation specification for the module.

## Project Structure

```text
src/channelflow/pipeline/passes.py                       # new
src/channelflow/pipeline/channel_main.py  resample_main.py   # use it
tests/unit/pipeline/test_passes.py   tests/mutations/passes.toml
docs/deployment.md                                        # a sentence
```

## Constitution Check

Principle XII (correctness precedes performance) and VII are not engaged beyond: the passes are unchanged; only
what happens when one fails. No violation; Complexity Tracking is empty.
