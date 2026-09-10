# Quickstart — validating activation latency

    make install
    .venv/bin/python -m pytest tests/unit/stops/ -q

Expected: passes, including the 20 pre-existing replay tests, which must be
unchanged — the default latency is smaller than the spacing of their paths, so
if one of them moves, the default is reaching past the example it came from.

To see the rule is load-bearing, make a decision effective immediately:

```python
# src/channelflow/stops/replay.py
while pending and pending[0][0] <= point.at_ns:   # was `<`
```

`test_the_prd_s_own_example` fails: the touch at `.180` exits on a stop
acknowledged at `.260`.

To see the tie rule is a rule rather than a preference, swap it the other way
and run the pair of tests that pay in opposite directions; exactly one of them
would pass under any outcome-chosen rule, and both must pass here.
