# Quickstart — validating the recording

    make install
    .venv/bin/python -m pytest tests/unit/pipeline -q

Expected: passes. Two are worth reading:

- `test_a_confirmation_arrives_in_its_own_bar_s_turn` — counts alternations,
  because "is the sequence sorted" passes for a batch at the end too;
- `test_a_longer_replay_adds_only_what_is_new` — idempotence rather than
  inertia.

    make lint && make typecheck && make test-fast
