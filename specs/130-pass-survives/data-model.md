# Data Model: pass survives

No data changes. State inside `run_passes`: the count of consecutive failed passes, reset by a success.

Lines printed (loop mode only):

| when | line |
|---|---|
| first failure of a run | `-- <name>: pass failed: <Type>: <message>` then the traceback |
| each later failure of the run | `-- <name>: pass failed again (<n> in a row): <Type>: <message>` |
| first success after failures | `-- <name>: recovered after <n> failed pass(es)` |
| after every pass | `-- next pass in <s>s` (unchanged) |
