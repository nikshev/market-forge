# Quickstart — validating the adoption

## Prerequisites

    make install

No services needed; every scenario below is a fast test.

## Scenario 1 — every module is checked, and none is listed

    .venv/bin/python -m pytest tests/unit/research/test_gate_adoption.py -q

Expected: passes, and the count of modules checked equals the number of `.py`
files in `src/channelflow/research/` other than `__init__.py`.

To see the check is real, temporarily add `src/channelflow/research/probe.py`
with an `EXPERIMENT` and a `COMPARISON` that has no `field` property. Expected:
red, and the failure names `probe`. Delete it afterwards.

## Scenario 2 — a field distinguishes its variants

    .venv/bin/python -m pytest tests/unit/experiments/test_fields.py -q

Expected: passes, including the case that decided the design — two
`RollingOLSChannel` variants differing only in `bands` produce different config
hashes and therefore two distinct registry rows.

## Scenario 3 — a field of eighteen experiments reaches the registry

    .venv/bin/python -m pytest tests/unit/research -q -k adoption

Expected: for each module, reporting its comparison leaves one row per variant,
and reporting it a second time leaves the same number.

## Scenario 4 — nothing an experiment computes has changed

    .venv/bin/python -m pytest tests/unit/research -q

Expected: passes unchanged. This is SC-009's check: the adoption adds a way to
ask a comparison what it compared; it must not alter a single metric.

## Full gate

    make lint && make typecheck && make test-fast
