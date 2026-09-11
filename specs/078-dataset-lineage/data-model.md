# Phase 1 — Data model

## `DatasetOrigin`

```python
@dataclass(frozen=True)
class DatasetOrigin:
    table: str
    snapshot_id: int
    content_hash: str

    @classmethod
    def of(cls, table: IcebergTable, snapshot_id: int | None = None) -> DatasetOrigin
```

Built from the table, so the hash is the one the plane computed. All three
fields required: a table name without a snapshot is a citation of "some of it",
and a snapshot without a hash is a name without a claim.

## `Resolution`

`RESOLVED`, `CHANGED`, `GONE`. Three, for the reason in the plan.

## `Registration`

Gains `dataset: DatasetOrigin`. **No default**, per [[ADR-015]]: a field with
one is a field an author can forget to think about, and this one selects whether
a result is checkable.

That makes thirteen fields against §23.9's eleven. The twelfth was
[[ADR-058]]'s `validation_regime`; the list describes the artifact and §0
governs.

## `CertifiedDataset`

Gains `origin: DatasetOrigin`, so a study has something to thread through. The
certificate already refuses to be built around an unclean report; it now also
refuses to be built around rows whose provenance nobody recorded.
