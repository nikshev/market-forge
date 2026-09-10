# Quickstart — validating the instrument rules

    make install

## Scenario 1 — the value refuses what it should

    .venv/bin/python -m pytest tests/unit/domain/test_instrument.py -q

Expected: passes, including a zero tick size, a negative step, a float, and a
zero contract size — each refused where the value is made.

## Scenario 2 — the venue's dialect stops at the connector

    .venv/bin/python -m pytest tests/unit/connectors -q

Expected: passes, including a missing `PRICE_FILTER` refused as **missing**
rather than as zero.

## Scenario 3 — both repositories answer alike

    .venv/bin/python -m pytest tests/unit/api -q

Expected: passes twice over, once per implementation, including a market stored
without rules reading back with them absent rather than zeroed.

## Full gate

    make lint && make typecheck && make test-fast
