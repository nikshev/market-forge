# Quickstart — validating the widened guard

## Prerequisites

    make install

## Scenario 1 — every package is scanned

    .venv/bin/python -m pytest tests/unit/extrema/test_live_causality.py -q

Expected: passes, and the count of modules scanned equals every `*.py` under
`src/channelflow/` less the exemptions.

To see it is real, add `from scipy.signal import savgol_filter` to
`src/channelflow/features/flow.py`. Expected: red, naming `features/flow.py` and
`savgol_filter`. Remove it afterwards.

## Scenario 2 — the exemption is exactly one module wide

Add the same import to `src/channelflow/extrema/detector.py`. Expected: red —
`extrema/causality.py` is exempt and its neighbours are not.

## Scenario 3 — an unsafe feature cannot be registered

    .venv/bin/python -m pytest tests/unit/features -q -k point_in_time

Expected: passes, including the case that constructing a `FeatureSpec` with
`point_in_time_safe=False` is refused.

## Full gate

    make lint && make typecheck && make test-fast
