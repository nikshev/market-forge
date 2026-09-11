# Phase 1 — Data model

## `BackupReport`

```python
table: str
snapshots: tuple[int, ...]     # copied, oldest first
objects: int                   # keys written
```

Names what was copied, so an interrupted run is legible afterwards.

## `RestoreReport`

```python
table: str
landed_on: int | None          # None for a table with no commits
newest_available: int | None
objects: int
```

`landed_on` is the requirement: a restore states where it landed. `None` is a
table that never had a commit, which is a different fact from an empty first
snapshot — a commit that never happened.

## `VerifyReport`

```python
missing: tuple[str, ...]        # manifest names it, the store does not have it
corrupt: tuple[str, ...]        # present, byte digest disagrees
identity_ok: bool               # content hash matches the source
ok: bool                        # all three clean
```

Three fields rather than a boolean, because "retry" and "disaster" are different
answers to the same 3am question.

## Errors

| | Raised when |
|---|---|
| `TargetNotEmpty` | anything exists under the table prefix in the target |
| `WouldLandShort` | the newest snapshot in the backup is not reachable and none was named |
| `NoSuchSnapshot` | reused from `table.py`; a named snapshot is not in the backup |
