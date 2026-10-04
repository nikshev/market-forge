# Contract: running a job's passes

1. Loop mode: a pass that raises `Exception` is reported, the interval is waited, the next pass runs.
2. The traceback is printed once per run of consecutive failures.
3. The first success after failures reports the recovery and the number of failed passes.
4. `--once`: a failing pass raises; a successful pass returns 0.
5. `KeyboardInterrupt` and `SystemExit` are never swallowed.
6. A healthy loop's output is unchanged.
