# Quickstart — validating the stop notification

    make install
    .venv/bin/python -m pytest tests/unit/alerting/ -q

Expected: passes, including the pre-existing alerting tests, which must be
unchanged — the dispatcher changed shape and the signal alert did not.

To see the message is a difference rather than a state, delete the old-stop
line from the renderer. The suite fails on the transition test, which asserts
both levels; a test asserting only the new stop would still pass, and that is
why the assertion is written as a pair.

To see the rate limit is real, set `debug=False` and offer a held proposal: zero
deliveries, one audit record naming the hold. Flip `debug=True` and the same
proposal is announced — under a header that is not "STOP UPDATED".
