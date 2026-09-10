# Contract — feed health and its announcement

```python
assess(readings, *, feed, at_ns, thresholds) -> FeedHealth
OutageWatch(gate=...).observe(health) -> AuditRecord | None
```

## Guarantees

- No readings at all yields a state that is not GOOD, with a reason saying
  nothing was reported.
- An absent individual reading is never counted as within its limit.
- Where several readings are bad, the worst state wins and the reason names it.
- `observe` returns a record on a change of state and `None` otherwise.
- A first observation in a bad state alerts; a first observation in GOOD does
  not, and neither does a recovery for a feed never alerted about.
- A recovery names the feed and how long it was bad; a duration of zero is a
  duration.
- The message shares no header with a trading signal or a stop update.
- Delivery, retry, dead-lettering and audit are the signal alert's.

## Does not

Produce readings. Nothing counts a reconnect or a gap yet; this assesses and
announces what it is handed.
