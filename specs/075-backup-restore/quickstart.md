# Quickstart — validating the round trip

    make install
    .venv/bin/python -m pytest tests/unit/lakehouse/test_backup.py -q

Expected: passes. For the real backend:

    make up
    .venv/bin/python -m pytest tests/integration/test_backup_on_minio.py -q

To see the ordering rule is load-bearing, replace the snapshot walk with the
obvious implementation:

```python
# src/channelflow/lakehouse/backup.py
for key in source.list(f"{name}/"):
    target.put_if_absent(key, source.get(key))
```

Every round-trip test still passes — the copy finishes, so nothing is missing.
`test_an_interrupted_backup_never_leaves_a_manifest_over_absent_data` is the one
that fails, because a sorted listing puts `metadata/` before the data directory
and an interruption then leaves exactly the corruption the writer refuses to
create.

That is the whole feature in one test, and it is why the tests interrupt the
copy rather than only completing it.
