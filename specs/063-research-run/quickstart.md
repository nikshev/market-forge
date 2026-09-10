# Quickstart — validating one research run

    make install
    .venv/bin/python -m pytest tests/unit/pipeline/test_study.py -q

Expected: passes. Three are worth reading:

- `test_the_fourth_hash_resolves_instead_of_reading_unrecorded` — the reason the
  requirement exists;
- `test_a_dirty_run_is_still_recorded_before_it_is_refused` — ADR-054's
  unconditional recording, at the point where it costs something;
- `test_a_variant_s_artifact_covers_its_folds_rather_than_one_of_them` — the
  claim a looser implementation would pass anyway.

    make lint && make typecheck && make test-fast
