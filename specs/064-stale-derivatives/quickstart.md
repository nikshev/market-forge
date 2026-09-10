# Quickstart — validating the freshness rule

    make install
    .venv/bin/python -m pytest tests/unit/derivatives -q

Expected: passes. Two are worth reading:

- `test_a_z_score_still_reads_the_history_behind_a_fresh_value` — the boundary a
  careless fix crosses, refusing the feature exactly when it has most to say;
- `test_open_interest_refuses_a_stale_reading_too` — the second reader, which no
  shared path covered.

    make lint && make typecheck && make test-fast
