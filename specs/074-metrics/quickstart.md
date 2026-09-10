# Quickstart — validating the exposition

    make install
    .venv/bin/python -m pytest tests/unit/metrics -q

Expected: passes.

To see the central rule is load-bearing, make registration create a series:

```python
# src/channelflow/metrics.py
def register(self, name, kind, help):
    ...
    self._series[name] = {(): 0.0}   # the convenient, dishonest default
```

`test_a_registered_metric_nobody_observed_is_absent` fails. That edit produces a
registry that behaves exactly like most metrics libraries, renders a complete
dashboard, and reports zero for every connector that has never run.

To see the pair matters, delete the zero-observation test instead: the mutation
above still fails, but an implementation that dropped observed zeroes would now
pass — which is why the two are asserted together.
