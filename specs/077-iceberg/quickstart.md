# Quickstart — the Iceberg-backed table

    make install
    .venv/bin/python -m pytest tests/unit/lakehouse/test_iceberg.py -q

Expected: passes, with no containers running — the catalog is a SQLite file and
the warehouse a temporary directory.

To see that knowledge and market time are two dimensions rather than one, make a
point-in-time read use the filter alone:

```python
# src/channelflow/lakehouse/iceberg.py
scan = table.scan(row_filter=...)          # dropping snapshot_id
```

`test_a_backfill_is_not_visible_to_an_earlier_read` fails. That edit produces a
read which returns every row with an early enough event time, including ones
appended long afterwards — the look-ahead Principle I forbids, arriving as a
correct-looking filter.

To see the same the other way, drop the filter and keep the snapshot: the same
test passes and `test_a_read_at_an_instant_excludes_later_rows` fails.
