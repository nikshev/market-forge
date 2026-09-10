# Quickstart — validating the bus

## Prerequisites

    make install

## Scenario 1 — the bus itself

    .venv/bin/python -m pytest tests/unit/test_bus.py -q

Expected: passes, including order, double subscription, mid-dispatch
subscription, and a propagating exception.

## Scenario 2 — the replay records exactly what it recorded before

    .venv/bin/python -m pytest tests/unit/pipeline -q

Expected: passes unchanged. This is SC-008 and the reason the rewiring is safe
to believe: the recorded bars, snapshots, signals and dataset identity are the
same values, reached by a different route.

## Scenario 3 — a second consumer costs one line

Subscribe a counter to `BarFinalized` in a scratch script and run a replay. The
producer's construction site is untouched — which is the whole claim.

## Full gate

    make lint && make typecheck && make test-fast
