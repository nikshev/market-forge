# Quickstart — validating calibration per horizon

    make install
    .venv/bin/python -m pytest tests/unit/models/test_calibration_by_horizon.py -q

Expected: passes. The test worth reading is
`test_the_pooled_figure_hides_what_the_slices_show` — one horizon well
calibrated, one badly, and the pooled error lands between them looking
tolerable. That is the requirement's whole argument, executable.

    make lint && make typecheck && make test-fast
