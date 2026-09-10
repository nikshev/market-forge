# Quickstart — validating outage alerts

    make install
    .venv/bin/python -m pytest tests/unit/health tests/unit/alerting -q

Expected: passes, including the pre-existing alerting tests unchanged.

To see the central rule is load-bearing, make an unreported metric count as
healthy:

```python
# src/channelflow/health.py
if readings.stale_ns is not None and readings.stale_ns > thresholds.stale_ns:
# becomes
if (readings.stale_ns or 0) > thresholds.stale_ns:
```

`test_nothing_reported_is_not_good_news` fails. That edit produces a working
assessment that returns GOOD for a feed which has stopped reporting entirely —
the exact case the alerting exists for, silenced by a default.

To see the ranking is real, swap two members of `HealthState` and run the
assessment tests: a stale feed outranks an invalid one and every state returned
still looks plausible.
