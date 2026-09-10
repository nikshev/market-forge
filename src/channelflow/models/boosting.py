"""PRD section 23.6's gradient boosted trees.

# @trace: REQ-EXP-008
# @trace: REQ-WP-018

[[ADR-029]] named the risk in building this rather than importing it:
"implementing them badly is worse than not having them, because a GMDH model
that beats a poor tree looks validated".

So this is deliberately the textbook version and nothing more -- depth-limited
regression trees on the logistic gradient, a fixed learning rate, a fixed count.
It is not competitive with LightGBM and does not pretend to be: what it provides
is a baseline that can find an interaction a linear model cannot, which is the
whole reason section 23.6 asks for a tree at all.

Every split is chosen by exhaustive search over the midpoints between observed
values, so the fit is deterministic without a seed. Ties break on the lowest
feature index and then the lowest threshold, for the same reason every other
tie-break in this repository is declared.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from channelflow.models.base import NotEnoughData, _sigmoid


@dataclass(frozen=True)
class TreeNode:
    """One decision, or a leaf holding a value."""

    feature: int | None = None
    threshold: float = 0.0
    left: TreeNode | None = None
    right: TreeNode | None = None
    value: float = 0.0

    @property
    def is_leaf(self) -> bool:
        return self.feature is None

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.is_leaf or self.left is None or self.right is None:
            return np.full(len(x), self.value)
        going_left = x[:, self.feature] <= self.threshold
        out = np.empty(len(x), dtype=np.float64)
        if going_left.any():
            out[going_left] = self.left.predict(x[going_left])
        if (~going_left).any():
            out[~going_left] = self.right.predict(x[~going_left])
        return out


@dataclass
class GradientBoostedTrees:
    """Section 23.6's tree baseline, in its simplest honest form."""

    name: str = "gradient_boosted_trees"
    trees: int = 30
    learning_rate: float = 0.1
    #: Two by default, which is the shallowest depth that can represent an
    #: interaction between two features. A depth of one is a stump, and a
    #: booster of stumps is additive in the features -- it cannot see what a
    #: linear model cannot, which is the whole reason section 23.6 asks for a
    #: tree ([[ADR-029]]'s "implementing them badly is worse than not having
    #: them").
    max_depth: int = 2
    #: A node with fewer rows than this is a leaf. Without it the tree splits
    #: down to single observations and memorizes the training fold.
    min_samples: int = 5
    _trees: list[TreeNode] = field(default_factory=list)
    _base: float = 0.0

    @property
    def fitted(self) -> bool:
        """Whether this model has learned anything.

        Only the model can answer: an unfitted booster has no trees, and a
        fitted one always has at least the first. [[REQ-WP-022]] asks because an
        artifact hash of an unfitted model is a stable, meaningless string that
        every unfitted model of its type would share.
        """
        return bool(self._trees)

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        share = float(np.clip(np.mean(y), 1e-6, 1 - 1e-6))
        self._base = float(np.log(share / (1.0 - share)))
        scores = np.full(len(y), self._base)
        self._trees = []

        for _ in range(self.trees):
            # The logistic gradient: where the model is wrong, and by how much.
            residual = y - _sigmoid(scores)
            tree = _grow(x, residual, depth=self.max_depth, min_samples=self.min_samples)
            if tree is None:
                break
            self._trees.append(tree)
            scores = scores + self.learning_rate * tree.predict(x)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if not self._trees:
            raise NotEnoughData("the model has not been fitted")
        scores = np.full(len(x), self._base)
        for tree in self._trees:
            scores = scores + self.learning_rate * tree.predict(x)
        result: np.ndarray = _sigmoid(scores)
        return result


def _grow(x: np.ndarray, residual: np.ndarray, *, depth: int, min_samples: int) -> TreeNode | None:
    """A regression tree over the residual, to `depth`.

    `None` at the root when no split improves on the mean: a tree that cannot
    beat not splitting is not a tree, and adding it moves the ensemble on noise.
    """
    if depth <= 0 or len(residual) < min_samples:
        return TreeNode(value=float(residual.mean()))

    found = _best_split(x, residual, min_samples=min_samples)
    if found is None:
        return TreeNode(value=float(residual.mean()))

    feature, threshold = found
    mask = x[:, feature] <= threshold
    left = _grow(x[mask], residual[mask], depth=depth - 1, min_samples=min_samples)
    right = _grow(x[~mask], residual[~mask], depth=depth - 1, min_samples=min_samples)
    return TreeNode(feature=feature, threshold=threshold, left=left, right=right)


def _best_split(
    x: np.ndarray, residual: np.ndarray, *, min_samples: int
) -> tuple[int, float] | None:
    """The split that best separates the residual, by squared error.

    Exhaustive over the midpoints between observed values, so there is nothing
    to seed. Strictly better wins, so a tie leaves the earlier split in place --
    features in order, thresholds ascending, which is the declared tie-break.
    """
    best: tuple[int, float] | None = None
    best_error = float(np.sum((residual - residual.mean()) ** 2))

    for feature in range(x.shape[1]):
        values = np.unique(x[:, feature])
        if len(values) < 2:
            continue
        for threshold in (values[:-1] + values[1:]) / 2.0:
            mask = x[:, feature] <= threshold
            if mask.sum() < min_samples or (~mask).sum() < min_samples:
                continue
            left, right = residual[mask].mean(), residual[~mask].mean()
            error = float(
                np.sum((residual[mask] - left) ** 2) + np.sum((residual[~mask] - right) ** 2)
            )
            if error < best_error:
                best_error = error
                best = (feature, float(threshold))
    return best
