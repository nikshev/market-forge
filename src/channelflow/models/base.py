"""The model abstraction (REQ-WP-018, PRD section 23).

# @trace: REQ-WP-018

One protocol, so a GMDH network and a baseline are interchangeable wherever a
score is being compared. PRD section 23.6 requires every GMDH result to be
reported beside its baselines on identical data, and that comparison is only
honest if the same code path produces both numbers.

Nothing here trains itself on construction. Fitting is explicit, so a caller
can see -- and a test can assert -- which rows a model was shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class Model(Protocol):
    """Anything that can be fitted and then asked for probabilities."""

    name: str

    def fit(self, x: np.ndarray, y: np.ndarray) -> None: ...

    def predict_proba(self, x: np.ndarray) -> np.ndarray: ...


class SplitOverlap(ValueError):
    """Two splits share rows, so one is not held out from the other."""


class NotEnoughData(ValueError):
    """Too little data for the result to mean anything."""


@dataclass
class BaseRate:
    """PRD section 23.6's first baseline: predict the training frequency.

    The one most models actually fail against. A classifier on an imbalanced
    target that always predicts the majority class scores well on accuracy and
    knows nothing -- so a model that cannot beat this is not a model.
    """

    name: str = "no_skill_base_rate"
    _rate: float = 0.5

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self._rate = float(np.mean(y)) if len(y) else 0.5

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return np.full(len(x), self._rate, dtype=np.float64)


@dataclass
class LogisticRegression:
    """PRD section 23.6's second baseline, over NumPy.

    Plain gradient descent with a fixed step and iteration count: deterministic
    by construction, which FR-012 requires and which a stochastic optimiser
    would break for no benefit at this scale.

    Not regularized. Section 23.6 asks for a regularized variant too, and an L2
    term with an unvalidated coefficient is not that baseline -- see ADR-029.
    """

    name: str = "logistic_regression"
    iterations: int = 400
    learning_rate: float = 0.1
    _weights: np.ndarray | None = None
    _bias: float = 0.0

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        features = x.shape[1]
        weights = np.zeros(features, dtype=np.float64)
        bias = 0.0
        rows = max(len(x), 1)
        for _ in range(self.iterations):
            predictions = _sigmoid(x @ weights + bias)
            error = predictions - y
            weights -= self.learning_rate * (x.T @ error) / rows
            bias -= self.learning_rate * float(np.sum(error)) / rows
        self._weights = weights
        self._bias = bias

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self._weights is None:
            raise NotEnoughData("the model has not been fitted")
        return _sigmoid(x @ self._weights + self._bias)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # Clipped before exponentiating: an unclipped exp overflows on a large
    # magnitude and returns nan, which then propagates through every score in
    # the report as a blank rather than as an error.
    result: np.ndarray = 1.0 / (1.0 + np.exp(-np.clip(z, -60.0, 60.0)))
    return result


def require_disjoint(fit_rows: np.ndarray, score_rows: np.ndarray) -> None:
    """ADR-030: splits that share rows are refused before anything is fitted.

    Comparing the two sets costs nothing. A search that quietly selected on its
    own training data would produce a plausible model and a good-looking
    report, and nothing downstream would contradict it.
    """
    shared = set(map(tuple, fit_rows.tolist())) & set(map(tuple, score_rows.tolist()))
    if shared:
        raise SplitOverlap(
            f"{len(shared)} row(s) appear in both the fitting and the scoring split. "
            "GMDH's external criterion means selecting on data the node did not "
            "see; an overlapping split silently turns the search into a memoriser"
        )
