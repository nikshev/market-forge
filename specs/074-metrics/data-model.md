# Phase 1 — Data model

## `MetricKind`

`COUNTER` and `GAUGE`. §33's list is counts and current values; a histogram
would need bucket boundaries nobody has chosen, and inventing them is the
"research default wearing a decision's clothes" this repository keeps refusing.

## `MetricRegistry`

```python
register(name, kind, help)      # records a metric; creates no series
observe(name, value, **labels)  # creates or updates one series
render() -> str                 # only observed series
```

Registration without observation is the load-bearing case: a registry holding
every §33 name and no observations renders an empty exposition.

`observe` on a counter refuses a value below the current one.

## `UNIMPLEMENTED`

A tuple naming each §33 metric this system does not produce, with the reason.
Named rather than exported as zero, and rather than dropped from the list —
those being the two failures the requirement is about.

## Derivations

```python
delivery_failures(audit)  -> int      # records whose status is not "delivered"
stale_feeds(healths)      -> int      # assessments whose state is not GOOD
```

Both read what the system already produces.
