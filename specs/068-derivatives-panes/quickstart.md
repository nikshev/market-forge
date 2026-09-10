# Quickstart — validating the panes

    make install
    .venv/bin/python -m pytest tests/unit/features/test_pane_features.py -q
    make web-test

Expected: passes. To see the check is real, misspell a feature in
`apps/web/src/panes.ts`; the Python suite fails naming it, and the browser tests
do not — which is the whole reason the check lives where it does.
