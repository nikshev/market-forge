# Phase 1 — Data model

## `HealthState`

```python
GOOD < DEGRADED < STALE < INVALID
```

PRD §32's four, ranked so the worst decides by comparison. The rank is tested
directly: mis-ordered, a stale feed outranks an invalid one and every assessment
still returns a plausible state.

## `HealthReadings`

Each field optional, and `None` means **not reported** — never "fine".

| Field | Bad when |
|---|---|
| `reconnects` | above the limit → DEGRADED |
| `missing_bars` | above the limit → DEGRADED |
| `stale_ns` | above the limit → STALE |
| `gap_rate` | above the limit → INVALID |
| `duplicate_rate` | above the limit → INVALID |

§32's other four metrics — chain RPC lag, subgraph indexing lag, insert delay,
latency percentiles — belong to systems that do not exist here. A field for one
of them would suggest something watches it.

## `HealthThresholds`

Every limit an argument with a stated default. §32 lists metrics and no values,
which is §13.11's situation: a constant here is a research default wearing a
decision's clothes.

## `FeedHealth`

```python
feed: str
state: HealthState
reason: str
observed_at_ns: int
```

The reason carries what the state approximates — "invalid because gappy" against
"invalid because silent".

## `OutageAlert` and `OutageWatch`

`OutageAlert` satisfies [[REQ-WP-034]]'s `Notification`: it identifies itself,
names the feed, renders and links.

`OutageWatch` holds the last state per feed and the instant it went bad. It
emits on a change and on nothing else.
