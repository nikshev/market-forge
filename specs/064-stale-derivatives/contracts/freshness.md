# Contract — freshness

```
require_fresh(newest_event_ns, *, at_ns, staleness_ns) -> None
```

Refuses with `StaleState` when `at_ns - newest_event_ns > staleness_ns`.
Refuses with `ValueError` when the tolerance is negative. The boundary is
inclusive: a reading exactly at the tolerance is fresh.

Age is measured from the **event** time. A correction arriving late describes an
old instant and is old.

## Called by

`state_at`, `settled_funding`, `oi_series` — each finds its newest observation
its own way, and each must call it. There is no shared seam that would cover a
fourth reader for free, and the next one has to remember.

## Does not

Constrain a z-score's window. `funding_z` reads a long history on purpose, and
refusing old history would break the feature the rule protects.
