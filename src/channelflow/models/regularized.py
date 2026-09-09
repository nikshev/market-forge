"""PRD section 23.6's regularized logistic baseline.

# @trace: REQ-EXP-008
# @trace: REQ-WP-018

[[ADR-029]] left this one out and said exactly why: "an L2 term with an
unvalidated coefficient is not the baseline section 23.6 asks for". The
objection was never the arithmetic -- it is forty lines -- but the coefficient,
which is a research decision that a default would make on the researcher's
behalf and then hide.

So the penalty strengths are required arguments. A caller states theirs, the
report carries them, and the baseline is somebody's declared choice rather than
this module's.

Elastic net rather than plain L2, because section 23.6 says "regularized" and
the elastic net contains both: set `l1_ratio` to zero and it is ridge, to one
and it is lasso. Fitted by proximal gradient descent -- the L1 term has no
gradient at zero, and soft-thresholding is what makes a coefficient actually
reach it rather than hover near it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from channelflow.models.base import NotEnoughData, _sigmoid


@dataclass
class ElasticNetLogistic:
    """Logistic regression with an L1 and L2 penalty, both declared.

    Deterministic: a fixed step and a fixed iteration count from a zero start,
    so two fits over one input agree exactly.
    """

    #: Overall penalty strength. No default: [[ADR-029]]'s objection.
    penalty: float = field(kw_only=True)
    #: How much of the penalty is L1. 0 is ridge, 1 is lasso.
    l1_ratio: float = field(kw_only=True)
    name: str = "regularized_logistic_regression"
    iterations: int = 400
    learning_rate: float = 0.1
    _weights: np.ndarray | None = None
    _bias: float = 0.0

    def __post_init__(self) -> None:
        if self.penalty < 0.0:
            raise ValueError("the penalty is a magnitude; a negative one rewards large weights")
        if not 0.0 <= self.l1_ratio <= 1.0:
            raise ValueError("l1_ratio is a share of the penalty and lies in [0, 1]")

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        rows, features = x.shape
        weights = np.zeros(features, dtype=np.float64)
        bias = 0.0
        l1 = self.penalty * self.l1_ratio
        l2 = self.penalty * (1.0 - self.l1_ratio)

        for _ in range(self.iterations):
            predictions = _sigmoid(x @ weights + bias)
            error = predictions - y
            gradient = (x.T @ error) / max(rows, 1) + l2 * weights
            stepped = weights - self.learning_rate * gradient
            # Soft-thresholding: the L1 term's subgradient does not vanish, so
            # a plain step leaves coefficients hovering near zero instead of at
            # it. This is the proximal operator that puts them there.
            threshold = self.learning_rate * l1
            weights = np.sign(stepped) * np.maximum(np.abs(stepped) - threshold, 0.0)
            bias -= self.learning_rate * float(np.sum(error)) / max(rows, 1)

        self._weights = weights
        self._bias = bias

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self._weights is None:
            raise NotEnoughData("the model has not been fitted")
        return _sigmoid(x @ self._weights + self._bias)
