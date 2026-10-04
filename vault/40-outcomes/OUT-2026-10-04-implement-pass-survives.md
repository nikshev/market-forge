---
id: OUT-2026-10-04-implement-pass-survives
step: implement
records: [REQ-INFRA-012]
commit: null
---

## What was done

`channelflow.pipeline.passes.run_passes` now owns the pass loop of the `worker` and `resample`. A pass that
raises an `Exception` in loop mode is reported with the job's name and the exception, the loop waits its
interval and runs the next pass, the traceback is printed once per run of failures, and the first success
after one says how many passes failed. `--once` still raises; an interrupt or an exit still stops the process.
A healthy loop prints exactly what it printed. The two mains call it; nothing else about a pass changed.

**RED, as run:** `ModuleNotFoundError: No module named 'channelflow.pipeline.passes'` (13 tests).

**After.** `tests/unit/pipeline/test_passes.py` 13 passed; the existing pipeline tests (238 in the directory)
pass unchanged; `make test` 3228 passed; lint and mypy clean. Mutation sweep `passes.toml`: **10 caught, 0
survived**. The sweep found one unpinned behaviour — the `-- next pass in` line, which FR-006 says must be
unchanged and no test asserted — and a test now pins the healthy output exactly. It also showed two mutations
that *hung* instead of failing (a loop that never sleeps never reaches the test's stop); the tests now end such
a loop themselves so a broken loop is a failed test, not a hung one.

**Live, 2026-10-04 06:01-06:09 UTC (SC-003).** A throwaway worker against an object store that cannot be
reached (`CHANNELFLOW_S3_ENDPOINT=http://127.0.0.1:1`), interval 5 s, watched for 40 s:

| | exit | what it said |
|---|---|---|
| old image | **1**, at the first pass | a traceback |
| new image | still running at 40 s (`timeout` killed it) | `pass failed` once with **one** traceback, then `pass failed again (2 … 6 in a row)` |

Six failure lines in 40 s, one traceback, and the loop never left.

## What was decided

- **Not deployed to the running `worker` and `resample` yet, on purpose.** Recreating them would restart the
  24-hour measurement of [[REQ-WP-079]], which ends at 07:18 UTC. They are recreated after that check; the
  new images are already built.
- **The sleep is injected** (`sleep=None` means `time.sleep` looked up at call time), so no test waits.
- **`except Exception`**, because the two incidents' causes (a snapshot race, an object-store 503) share
  nothing, so no list of known causes would have covered both.

## What is still open

- Deployment to the running services (above).
- A failure that never clears prints a line every interval; alerting on it belongs with the observability
  work, not here.
