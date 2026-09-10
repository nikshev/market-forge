# Contract — recording extrema

`record_replay` additionally:

1. runs a `DirectionalChangeDetector` over the same bars;
2. publishes `ExtremumObserved` as each candidate appears and
   `ExtremumConfirmed` in the turn of the bar that confirmed it;
3. records both through subscribers, never by writing directly;
4. skips what the tables already hold, per series, on knowledge.

`Recording.confirmed_extrema` and `.extremum_candidates` are what this run
wrote; `.skipped` is what every recorder declined.

## Does not

Change the detector, the runner, or what a replay already records. The dataset
identity of bars, snapshots and signals is unchanged, and a test asserts it.
