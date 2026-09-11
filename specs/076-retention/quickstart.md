# Quickstart — validating retention

    make install
    .venv/bin/python -m pytest tests/unit/lakehouse/test_retention.py -q

Expected: passes, with no containers running.

To see that the pass actually frees bytes — the thing the hand-rolled plane
could not do, and the reason for [[ADR-060]] — count the parquet files in the
warehouse before and after. They drop. On the old format they would not have,
because every data file stayed referenced by the newest snapshot forever.

To see the pin is load-bearing, pin the oldest snapshot and run a policy that
would expire it. It survives, and the report says why. Remove the pin and it
goes.

To see the capability rule is asserted rather than assumed, add
`self.io.delete(path)` to any module other than `retention.py`:
`test_only_retention_deletes` fails, naming the file ([[ADR-062]]).
