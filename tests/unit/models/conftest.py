"""Deterministic datasets with known structure (REQ-WP-018)."""

from __future__ import annotations

import numpy as np
import pytest


def separable(rows: int = 200, *, seed: int = 11) -> tuple[np.ndarray, np.ndarray]:
    """A target that genuinely depends on an interaction of two inputs.

    `y` turns on `x0 * x1`, which no linear model can capture and a quadratic
    node can. If GMDH cannot beat logistic regression here it is not working;
    a fixture where both do equally well would prove nothing either way.
    """
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1.0, 1.0, size=(rows, 4))
    y = (x[:, 0] * x[:, 1] > 0.0).astype(np.float64)
    return x, y


def noise(rows: int = 200, *, seed: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """A target with no relationship to its inputs at all.

    The dataset every honest model should fail on. A search that grows layers
    here is memorising, and the comparison report should say the model does not
    beat the base rate.
    """
    rng = np.random.default_rng(seed)
    return rng.uniform(-1.0, 1.0, size=(rows, 4)), rng.integers(0, 2, size=rows).astype(np.float64)


@pytest.fixture
def structured() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit and score splits with no shared rows."""
    x, y = separable(300)
    return x[:200], y[:200], x[200:], y[200:]


@pytest.fixture
def unstructured() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x, y = noise(300)
    return x[:200], y[:200], x[200:], y[200:]
