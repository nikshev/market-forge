# Contract — the Iceberg-backed table

```python
catalog(uri, warehouse) -> Catalog
IcebergTable(name, schema, catalog) 
    .append(rows) -> TableSnapshot
    .read(snapshot_id=None, as_of_ns=None) -> pa.Table
    .snapshot_ids() -> tuple[int, ...]
    .snapshot(n) -> TableSnapshot
    .current() -> TableSnapshot | None
    .unreferenced_files() -> tuple[str, ...]
```

## Guarantees

- A read at an instant excludes rows whose event time is later, within the
  snapshot asked for: knowledge and market time, composed, never one standing in
  for the other.
- Appending never changes what an earlier read returned.
- A commit is atomic; a loser in a race is refused and nothing of it is visible.
- `content_hash` is over rows in the schema's canonical encoding, equal across
  processes and library versions for equal data.
- A point-in-time read on a table with no event-time column is refused, not
  answered with everything.
- An empty append is refused.
- `unreferenced_files` lists exactly what no live snapshot plans, which is what
  retention may remove and nothing else.
- Nothing reads a clock.

## Does not

Migrate callers, delete anything, or remove the hand-rolled format. Those are
later steps of [[REQ-WP-039]], and the requirement stays open until they land.
