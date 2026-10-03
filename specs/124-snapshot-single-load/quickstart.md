# Quickstart: proving a snapshot read resolves against one version

## 1. The proof (fast gate, no services)

    .venv/bin/python -m pytest tests/unit/lakehouse/test_single_load.py -q

Before the change this fails: loads are 2, 5, 5, 7 where 1 is expected, and the racing wrapper
raises `NoSuchSnapshot`. After it, all pass.

## 2. The count, by hand

    PYTHONPATH=. .venv/bin/python specs/124-snapshot-single-load/count_loads.py

(the script from planning, kept beside the spec). Expected after: one load per row.

## 3. Evidence against a real catalog

    .venv/bin/python -m pytest tests/integration/test_snapshot_race.py -q

A reader looping beside a writer looping. Evidence only: it can pass by luck on unfixed code.

## 4. The deployment

After rebuilding every service that imports the lakehouse, and a full day of running:

    docker compose logs worker resample | grep -c NoSuchSnapshot   # expect 0

Record the date and the count in the implement outcome note. Before: 14 in about 13 hours.
