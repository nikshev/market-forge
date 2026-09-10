# Quickstart — validating positioning

    make install
    .venv/bin/python -m pytest tests/unit/derivatives/ -q

Expected: passes, 16 of them in `test_positioning.py`.

To see the central distinction is load-bearing rather than decorative, make
absence default to a balanced book:

```python
# src/channelflow/derivatives/positioning.py
return state_at(...).long_short_ratio or 1.0
```

The suite fails on `test_a_ratio_nobody_published_reads_as_nothing`. Restore it,
then delete the `if s.meta.event_time_ns <= at_ns` filter in `_z`: the suite
fails on the look-ahead test instead. Both edits produce a working module that
returns plausible numbers for every input — which is why each has a test naming
what it broke.

Registration is checked in the same file:

    .venv/bin/python -m pytest tests/unit/derivatives/test_positioning.py -k registered -q
