# Phase 1 — Data model

## `IcebergTable`

The surface the hand-rolled table already has:

```python
append(rows) -> TableSnapshot
read(*, snapshot_id: int | None = None, as_of_ns: int | None = None) -> pa.Table
snapshot_ids() -> tuple[int, ...]
snapshot(snapshot_id: int) -> TableSnapshot
current() -> TableSnapshot | None
unreferenced_files() -> tuple[str, ...]
```

Snapshot ids are `1, 2, 3` in commit order, mapped to Iceberg's allocated 64-bit
ids inside. Callers keep their meaning; FR-010 holds.

## `TableSnapshot`

```python
snapshot_id: int          # ours: small, sequential
iceberg_id: int           # theirs: allocated
parent_id: int | None
record_count: int
event_time_max_ns: int
content_hash: str         # over rows, ADR-053's rule
```

`content_hash` is a digest over the rows the snapshot can see, in the schema's
canonical encoding — writer-independent by construction, which is the whole
point of [[ADR-053]].

## Catalog

```python
catalog(uri: str, warehouse: str) -> Catalog
```

SQLite URI and a local directory for tests and the fast gate; a PostgreSQL URI
and an S3 warehouse elsewhere. One implementation, two URLs.
