# Quickstart — validating dataset lineage

    make install
    .venv/bin/python -m pytest tests/unit/models tests/unit/lakehouse/test_retention.py -q

Expected: passes.

To see the third outcome earn its place, make `resolve` answer on the id alone:

```python
# src/channelflow/models/registry.py
return Resolution.RESOLVED if origin.snapshot_id in table.snapshot_ids() else Resolution.GONE
```

`test_a_snapshot_that_now_holds_something_else_is_not_the_same_dataset` fails.
That edit produces a resolver which reports a citation as good whenever the name
still exists — which is precisely the case a citation is for.

To see the loop close, run a retention pass with pins from a registry and one
without: the registered snapshot survives the first and not the second.
