# Phase 1 — Data model

## `RetentionPolicy`

```python
@dataclass(frozen=True)
class RetentionPolicy:
    keep_ns: int          # no default
```

How much event-time history is worth keeping. **No default**, because PRD
§6.4.9 declines to name one — "suggested semantics, not hard-coded durations" —
and a number written here would be a research default wearing a decision's
clothes. The operator choosing one is choosing what their system forgets.

## `RetentionReport`

```python
table: str
cutoff_ns: int              # what "old" meant on this run
snapshots_before: int
snapshots_after: int
files_removed: int
kept: tuple[str, ...]       # every snapshot kept against the policy, and why
```

`kept` carries reasons rather than counts: "snapshot 3 is pinned" and "snapshot
7 is the newest" are the two facts somebody re-reading a pass needs, and a
number tells them neither.

## Errors

| | Raised when |
|---|---|
| `NoSuchPin` | a pin names a snapshot the table does not have |
| `NoEventTime` | reused; a table with no event time has no notion of old |

## What the pass touches

Iceberg's `delete` and `expire_snapshots`, then the files no live snapshot
plans. Nothing else, and nothing outside the table it was given.
