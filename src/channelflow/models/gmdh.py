"""The GMDH layered polynomial search (REQ-WP-018, PRD section 23).

# @trace: REQ-WP-018
# @trace: REQ-WP-019

Each node is a quadratic in two inputs:

    y_hat = a0 + a1*u + a2*v + a3*u*v + a4*u^2 + a5*v^2

A layer fits every pair, scores each on data it did not see, keeps the best
few, and their outputs become the next layer's inputs. The search stops when a
layer fails to improve.

The **external criterion** is the whole method (ADR-030): fit on one split,
select on another. A search that scored nodes on their own training rows would
grow layers as long as it was allowed to -- each layer can always fit the
sample better -- and every number afterwards would describe a memorised sample
while looking excellent.

Constitution Principle IV allows this to exist at all: deterministic baselines
are built (REQ-WP-006, REQ-WP-007, REQ-WP-019) and their leakage tests pass
(REQ-NRT-A to E, REQ-WP-017).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from channelflow.models.base import NotEnoughData, require_disjoint

#: Six terms: constant, both linear, the interaction, both quadratic.
TERMS = 6


class StopReason(StrEnum):
    """Why the search ended. Always reported (FR-005)."""

    NO_IMPROVEMENT = "a layer did not improve on the previous best"
    LAYER_BUDGET = "the maximum layer count was reached"
    NO_SURVIVORS = "every node in a layer was dropped"
    TOO_FEW_INPUTS = "fewer than two inputs remained to pair"


@dataclass(frozen=True)
class Node:
    """One fitted polynomial, and where its inputs came from."""

    layer: int
    left: int
    right: int
    coefficients: np.ndarray
    score: float

    def predict(self, u: np.ndarray, v: np.ndarray) -> np.ndarray:
        result: np.ndarray = _design(u, v) @ self.coefficients
        return result


@dataclass(frozen=True)
class SearchResult:
    """The layers, why the search stopped, and what it discarded."""

    layers: tuple[tuple[Node, ...], ...]
    stop_reason: StopReason
    dropped_singular: int
    best_score: float

    @property
    def depth(self) -> int:
        return len(self.layers)


@dataclass
class GMDHNetwork:
    """A layered polynomial network, grown under a complexity budget."""

    name: str = "gmdh"
    max_layers: int = 4
    survivors_per_layer: int = 6
    _result: SearchResult | None = None
    _input_names: tuple[str, ...] = field(default_factory=tuple)

    def fit_with_selection(
        self,
        x_fit: np.ndarray,
        y_fit: np.ndarray,
        x_score: np.ndarray,
        y_score: np.ndarray,
        *,
        input_names: tuple[str, ...] | None = None,
    ) -> SearchResult:
        """Grow layers, selecting on `x_score` -- data no node was fitted on."""
        require_disjoint(x_fit, x_score)
        if x_fit.shape[1] < 2:
            raise NotEnoughData("a GMDH search needs at least two inputs to pair")
        if len(x_score) < 2:
            raise NotEnoughData(
                "the scoring split has fewer than two rows; a criterion computed on "
                "one row selects noise"
            )
        if len(np.unique(y_fit)) < 2:
            raise NotEnoughData(
                "the target is constant, so every model predicts it perfectly and "
                "the comparison would be meaningless"
            )

        self._input_names = input_names or tuple(f"x{i}" for i in range(x_fit.shape[1]))

        layers: list[tuple[Node, ...]] = []
        current_fit, current_score = x_fit, x_score
        best_so_far = float("inf")
        dropped = 0
        reason = StopReason.LAYER_BUDGET

        for layer_index in range(self.max_layers):
            if current_fit.shape[1] < 2:
                reason = StopReason.TOO_FEW_INPUTS
                break

            candidates: list[Node] = []
            for left in range(current_fit.shape[1]):
                for right in range(left + 1, current_fit.shape[1]):
                    coefficients = _fit_node(current_fit[:, left], current_fit[:, right], y_fit)
                    if coefficients is None:
                        # A singular fit means those two inputs carry no
                        # independent information on this split. Dropped and
                        # counted rather than approximated.
                        dropped += 1
                        continue
                    predicted = (
                        _design(current_score[:, left], current_score[:, right]) @ coefficients
                    )
                    candidates.append(
                        Node(
                            layer=layer_index,
                            left=left,
                            right=right,
                            coefficients=coefficients,
                            # The external criterion: mean squared error on rows
                            # this node was never fitted on.
                            score=float(np.mean((predicted - y_score) ** 2)),
                        )
                    )

            if not candidates:
                reason = StopReason.NO_SURVIVORS
                break

            candidates.sort(key=lambda n: n.score)
            survivors = tuple(candidates[: self.survivors_per_layer])
            layer_best = survivors[0].score

            if layer_best >= best_so_far:
                # Growing further would be fitting noise: the criterion is
                # computed on held-out data, so a layer that does not improve
                # it is not finding structure.
                reason = StopReason.NO_IMPROVEMENT
                break

            best_so_far = layer_best
            layers.append(survivors)
            current_fit = np.column_stack(
                [n.predict(current_fit[:, n.left], current_fit[:, n.right]) for n in survivors]
            )
            current_score = np.column_stack(
                [n.predict(current_score[:, n.left], current_score[:, n.right]) for n in survivors]
            )

        self._result = SearchResult(
            layers=tuple(layers),
            stop_reason=reason,
            dropped_singular=dropped,
            best_score=best_so_far,
        )
        return self._result

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        """The `Model` protocol's fit, which GMDH cannot honestly provide.

        Selection needs a second split, and inventing one here would pick a
        rule -- random, chronological -- that PRD section 41 rules 1 and 10 are
        specifically about. Use `fit_with_selection`.
        """
        raise NotEnoughData(
            "GMDH needs a separate selection split; call fit_with_selection. "
            "Splitting here would choose a rule the caller should choose (ADR-030)"
        )

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Run the surviving path forward, unclipped.

        The network fits by least squares against a continuous target, so its
        output is continuous too. PRD section 13A.11 needs it that way: a
        forward price path squashed into `[0, 1]` is not a price path
        (REQ-WP-019).
        """
        if self._result is None or not self._result.layers:
            raise NotEnoughData("the network has not been fitted")
        current = x
        for layer in self._result.layers:
            current = np.column_stack(
                [n.predict(current[:, n.left], current[:, n.right]) for n in layer]
            )
        output: np.ndarray = current[:, 0]
        return output

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        """The same output, squashed to [0, 1] for a probability target."""
        clipped: np.ndarray = np.clip(self.predict(x), 0.0, 1.0)
        return clipped

    def interactions(self) -> tuple[tuple[str, str, int], ...]:
        """Which input pairs survived, resolved to original names (FR-008).

        PRD section 23.1's first named role for GMDH is interaction discovery,
        and a model that predicts without saying what it combined is not doing
        that job. Node indices are resolved back through the layers, so the
        answer is in the caller's vocabulary rather than the search's.
        """
        if self._result is None:
            return ()

        # Layer 0's inputs are the originals; each later layer's input `i` is
        # the previous layer's surviving node `i`, whose own names are already
        # resolved.
        names: list[tuple[str, ...]] = [self._input_names]
        found: list[tuple[str, str, int]] = []
        for depth, layer in enumerate(self._result.layers):
            available = names[depth]
            resolved: list[tuple[str, ...]] = []
            for node in layer:
                left, right = available[node.left], available[node.right]
                found.append((left, right, depth))
                resolved.append(tuple(sorted({*_split(left), *_split(right)})))
            names.append(tuple(" & ".join(r) for r in resolved))
        return tuple(found)


def _split(name: str) -> list[str]:
    return name.split(" & ")


def _design(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones_like(u), u, v, u * v, u**2, v**2])


def _fit_node(u: np.ndarray, v: np.ndarray, y: np.ndarray) -> np.ndarray | None:
    """Least squares for one node, or `None` when the design is singular."""
    design = _design(u, v)
    if design.shape[0] < TERMS:
        return None
    try:
        coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    if rank < TERMS:
        return None
    fitted: np.ndarray = coefficients
    return fitted
