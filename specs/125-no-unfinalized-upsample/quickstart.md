# Quickstart: proving the seam

## 1. The proof (no services)

    .venv/bin/python -m pytest tests/unit/test_upsample_seam.py -q

Before the change: 4 failed, 7 passed. After: all pass, in under a minute.

## 2. The violations are seen (US4)

    .venv/bin/python -m tools.mutate tests/mutations/resample_leak.toml
    .venv/bin/python -m tools.mutate tests/mutations/bars_as_of.toml

Each mutation is a leak put back; each is reported **caught** by name. A survivor needs a recorded
reason or the sweep fails.

## 3. By hand

    PYTHONPATH=. .venv/bin/python specs/125-no-unfinalized-upsample/probe.py

Before: bars=1 for the repeated-minute and non-final windows. After: bars=0, refusals=1.

## 4. On the deployment

The resample job's log lists `refused: window …` lines per pass; after the change those lines may
also carry `duplicated` or `not final`. There should be none of either on the current data.
