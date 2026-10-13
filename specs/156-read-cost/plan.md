# Implementation Plan: The cost of a read and of a pass

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-104]]

## Design decisions, with what was rejected

1. **One read, one commit per resample pass**: `run_pass` reads the table once, builds what each target holds from that read, computes
   every series, appends once. Rejected: caching reads between series (a second place to be stale); per-series commits kept "for
   isolation" (a failed series is isolated by its own `try`, the commit is of what succeeded).
2. **`narrow` in `tables/rows.py`**, applied in `read_bars`, `feature_points`, the consensus reads and `read_bins`. Rejected: pushing
   the filter into the Iceberg scan -- the table module's own `read` is the one place that decides commit order and as-of.
3. **Maintenance names its tables, and a test walks `tables/` for the ones it does not name.** Rejected: discovering them (the list
   is a decision; the test is what stops it being a forgotten one).
4. **An hourly interval by default**, because the files accumulate all day.

## Phases

1. Tests (resample pass, narrow, maintenance coverage). 2. Implementation. 3. Mutation sweeps. 4. Deploy (resample, API, maintenance) and
   measure.
