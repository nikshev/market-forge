"""Run a background job's passes, surviving the ones that fail (REQ-INFRA-012).

# @trace: REQ-INFRA-012

The `worker` and `resample` are loops: a pass over the stored bars, a sleep, another pass. Inside a
pass each series is guarded, so one that fails is printed and skipped. The first read of a pass is
not, and an exception there used to leave `main`, end the process, and rely on compose to start it
again. That happened twice on 2026-10-03 for unrelated reasons -- a `NoSuchSnapshot` race, and an
HTTP 503 from the object store under load -- and a transient fault in a dependency should cost one
pass, not a process.

**Reported once, survived, and the recovery reported.** The first failure of a run prints the
exception and its traceback; each further failure of the run prints one line; the first success
after it says how many passes failed. A storage outage of an hour would otherwise print a dozen
tracebacks, and a repeated condition does not repeat its full report ([[REQ-WP-078]]'s rule).

**`--once` is not a loop.** With no next pass to try, surviving would turn a failure into a silent
success, so it raises as it always did. And only `Exception` is caught: an interrupt or an exit must
still stop the process.

The interval is fixed, not backed off: a backoff would hide how long recovery takes behind a number
that grows, and a pass is cheap compared with its interval."""

from __future__ import annotations

import time
import traceback
from collections.abc import Callable


def run_passes(
    name: str,
    one_pass: Callable[[], object],
    *,
    interval_seconds: float | None,
    sleep: Callable[[float], object] | None = None,
) -> int:
    """Run `one_pass` once, or for ever when there is an interval, surviving failures there."""
    failed_in_a_row = 0
    while True:
        try:
            one_pass()
        except Exception as error:
            if interval_seconds is None:
                raise
            failed_in_a_row += 1
            summary = f"{type(error).__name__}: {error}"
            if failed_in_a_row == 1:
                print(f"-- {name}: pass failed: {summary}", flush=True)
                print(traceback.format_exc(), flush=True)
            else:
                print(
                    f"-- {name}: pass failed again ({failed_in_a_row} in a row): {summary}",
                    flush=True,
                )
        else:
            if failed_in_a_row:
                print(f"-- {name}: recovered after {failed_in_a_row} failed pass(es)", flush=True)
                failed_in_a_row = 0
        if interval_seconds is None:
            return 0
        print(f"-- next pass in {interval_seconds:.0f}s", flush=True)
        (sleep or time.sleep)(interval_seconds)
