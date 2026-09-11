# Quickstart — the event backbone

    make install
    .venv/bin/python -m pytest tests/unit/transport -q

Expected: passes, with no broker.

For the real thing:

    make up
    .venv/bin/python -m pytest tests/integration/test_transport_on_redpanda.py -q

To see the replay rule is load-bearing, have the materialising consumer write
the table itself instead of going through `record_bars`:

```python
# src/channelflow/transport/materialise.py
bars_table.table_for(catalog).append(rows)     # skipping the watermark
```

`test_consuming_a_topic_twice_writes_its_rows_once` fails: the second pass
appends every bar again. That is the defect [[ADR-056]] exists because of, and
it is exactly what a sink connector would have done ([[ADR-063]]).
