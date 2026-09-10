# Quickstart — validating the markers

    make install && make web-install
    .venv/bin/python -m pytest tests/unit/tables/test_extrema.py tests/unit/api -q
    make web-test

Expected: passes. The pair worth reading, one on each side:

- `test_a_turn_is_not_returned_before_it_was_confirmed` — the acceptance
  criterion at the layer that enforces it;
- `test_a_returned_turn_still_carries_the_instant_it_happened` — the half a
  looser implementation drops, satisfying the criterion by drawing the turn in
  the wrong place.

    make lint && make typecheck && make test-fast && make web-typecheck && make web-build
