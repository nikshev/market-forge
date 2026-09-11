# Quickstart — validating the round trip

    make install
    .venv/bin/python -m pytest tests/unit/lakehouse/test_backup.py -q

Expected: passes. For the real backend:

    make up
    .venv/bin/python -m pytest tests/integration/test_backup_on_minio.py -q

To see what the ordering rule costs and what it buys, replace the snapshot walk
with the obvious implementation:

```python
# src/channelflow/lakehouse/backup.py
for key in source.list(f"{name}/"):
    target.put_if_absent(key, source.get(key))
```

Every test still passes, including the interruption one: `data/` sorts before
`metadata/`, so a sorted listing copies data first and is safe for this layout.
That is recorded rather than hidden — the mutation sweep found it — and the
argument for the walk is not that the listing is broken but that it is safe by
coincidence of two directory names.

To see the coincidence, rename the data directory in `table.py` to something
sorting after `metadata` and run the interruption test against the listing
implementation. It fails, and it fails the way the writer refuses to fail: a
manifest naming files that never arrived.

The interruption tests still matter most, because the ordering they check is the
only property here that a completed copy cannot demonstrate.
