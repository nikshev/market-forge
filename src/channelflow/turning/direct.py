"""PRD section 13A.13's direct target, and the baseline it must beat.

# @trace: REQ-WP-019
# @trace: REQ-US-007

    "Do not depend only on a derivative-based target. Build direct supervised
     targets too."

Section 23.5A's Target E is the target: `P(local_max_within_H | state_t)` and
its two siblings. REQ-WP-017 already builds those labels with their availability
shifted to confirmation time; this module turns labelled rows into a matrix and
scores a model on them fold by fold.

The model here is the logistic baseline itself -- REQ-WP-019's item 11, "direct
logistic/boosted baseline". Scoring it against `BaseRate` is the comparison that
matters: a Brier score alone reads like a result, and against a no-skill base
rate it reads like what it is.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, get_args

import numpy as np

from channelflow.dataset import CertifiedDataset, LabelClass, Row
from channelflow.models import ComparisonReport, LogisticRegression, NotEnoughData, compare

#: Section 23.5A's Target E, in the PRD's order.
HORIZON_TARGETS: tuple[LabelClass, ...] = get_args(LabelClass)

Target = Literal["MAX", "MIN", "NO_TURN"]


class FeatureMissing(ValueError):
    """A row does not carry a feature the matrix declares."""


@dataclass(frozen=True)
class DirectBaselineResult:
    """Per-fold reports and the aggregate over them."""

    folds: tuple[ComparisonReport, ...]
    rows_scored: int
    model_brier: float | None
    base_rate_brier: float | None
    #: Folds dropped because the target never occurred in them, with the reason.
    unscored: tuple[str, ...] = ()

    @property
    def beats_base_rate(self) -> bool:
        """Lower Brier is better; a tie is not a win, and no folds is not one either."""
        if self.model_brier is None or self.base_rate_brier is None:
            return False
        return self.model_brier < self.base_rate_brier

    @property
    def summary(self) -> str:
        if not self.folds:
            return (
                f"no fold could be scored ({len(self.unscored)} dropped): "
                f"{'; '.join(self.unscored)}"
            )
        if not self.beats_base_rate:
            return (
                f"over {len(self.folds)} fold(s) and {self.rows_scored} rows the direct "
                "baseline does not beat the no-skill base rate; nothing here is "
                "evidence of skill"
            )
        return (
            f"over {len(self.folds)} fold(s) and {self.rows_scored} rows the direct "
            f"baseline beats the no-skill base rate ({self.model_brier:.4f} against "
            f"{self.base_rate_brier:.4f})"
        )


def design_matrix(
    rows: list[Row], *, target: Target, feature_names: tuple[str, ...]
) -> tuple[np.ndarray, np.ndarray]:
    """Features in the declared order, and a binary column for `target`.

    The order is the caller's, never the dictionary's: a matrix whose columns
    follow insertion order changes meaning when a row is built differently, and
    every coefficient silently changes with it.
    """
    if target not in HORIZON_TARGETS:
        raise ValueError(
            f"target {target!r} is not one of section 23.5A's Target E classes {HORIZON_TARGETS}"
        )
    if not feature_names:
        raise ValueError("a design matrix needs at least one feature")

    values = []
    for row in rows:
        missing = [name for name in feature_names if name not in row.features]
        if missing:
            raise FeatureMissing(
                f"row at {row.as_of_ns} does not carry {', '.join(missing)}; a missing "
                "feature defaulted to zero says 'none' where it means 'unknown', and "
                "nothing downstream can tell the two apart"
            )
        values.append([row.features[name] for name in feature_names])

    x = np.array(values, dtype=np.float64)
    y = np.array(
        [1.0 if row.label.label_class == target else 0.0 for row in rows], dtype=np.float64
    )
    return x, y


def run_direct_baseline(
    dataset: CertifiedDataset, *, target: Target, feature_names: tuple[str, ...]
) -> DirectBaselineResult:
    """Fit and score fold by fold, and aggregate weighted by rows scored.

    Takes a `CertifiedDataset`, never a bare fold list: REQ-US-007 asks that the
    training data pass the leakage checks *before* being trained on, and a
    precondition someone has to remember is not a guarantee.

    A fold whose target never occurs is dropped with its reason rather than
    scored: a constant target makes every model perfect, and averaging that in
    would raise the reported quality of a model that learned nothing.
    """
    reports: list[ComparisonReport] = []
    unscored: list[str] = []

    for fold in dataset.folds:
        x_fit, y_fit = design_matrix(list(fold.train), target=target, feature_names=feature_names)
        x_score, y_score = design_matrix(
            list(fold.validate), target=target, feature_names=feature_names
        )
        if len(np.unique(y_fit)) < 2 or len(np.unique(y_score)) < 2:
            unscored.append(
                f"fold {fold.index}: the target {target!r} is constant on one of its splits"
            )
            continue
        try:
            reports.append(
                compare(
                    # A fresh model per fold. Reusing one would carry the
                    # previous fold's weights into this fold's fit.
                    LogisticRegression(),
                    x_fit=x_fit,
                    y_fit=y_fit,
                    x_score=x_score,
                    y_score=y_score,
                )
            )
        except NotEnoughData as exc:
            unscored.append(f"fold {fold.index}: {exc}")

    return aggregate(reports, unscored)


def aggregate(reports: list[ComparisonReport], unscored: list[str]) -> DirectBaselineResult:
    """Rows-weighted aggregate over per-fold reports.

    Shared with the derivative experiment: both score fold by fold and both must
    weight by rows, so a fold of three rows does not count like one of thirty.
    """
    rows_scored = sum(report.rows_scored for report in reports)
    return DirectBaselineResult(
        folds=tuple(reports),
        rows_scored=rows_scored,
        model_brier=_weighted(reports, lambda r: r.model.brier, rows_scored),
        base_rate_brier=_weighted(reports, lambda r: r.base_rate.brier, rows_scored),
        unscored=tuple(unscored),
    )


def _weighted(
    reports: list[ComparisonReport],
    pick: Callable[[ComparisonReport], float | None],
    rows_scored: int,
) -> float | None:
    """Rows-weighted mean, so a fold of three rows does not count like one of thirty."""
    if not reports or rows_scored == 0:
        return None
    total = 0.0
    for report in reports:
        score = pick(report)
        if score is None:
            return None
        total += float(score) * report.rows_scored
    return total / rows_scored
