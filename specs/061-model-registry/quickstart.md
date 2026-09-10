# Quickstart — validating the model registry

    make install
    .venv/bin/python -m pytest tests/unit/models/test_registry.py -q

Expected: passes, including the four cases the mutation sweep added — a
hyperparameter changed without refitting, a difference below printing precision,
an array reshaped without changing a byte, and a mapping that collides unframed.

    .venv/bin/python -m pytest tests/unit/experiments -q

Expected: unchanged. The gate is extended, not altered.

    make lint && make typecheck && make test-fast
