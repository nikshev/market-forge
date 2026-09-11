# Contract — dataset lineage

```python
DatasetOrigin.of(table, snapshot_id=None) -> DatasetOrigin
resolve(origin, table) -> Resolution
pins_for(registry, table_name) -> tuple[int, ...]
```

## Guarantees

- Every registration names a table, a snapshot and that snapshot's content hash.
- A registration without a dataset is refused at construction.
- `resolve` distinguishes matching, changed and gone; a changed snapshot is
  never reported as fine because its id still exists.
- An unresolvable dataset never prevents a registration from being read.
- `pins_for` returns exactly the snapshots registrations name for that table,
  each once, and an empty tuple when there are none.

## Does not

Decide what to do about a stale citation. Whether `require_registered` should
refuse one is left open in the spec, because making it fatal would also make
every report unreadable after a legitimate retention pass.
