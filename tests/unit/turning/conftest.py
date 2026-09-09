"""Rows for the direct turning-point target (REQ-WP-019, PRD section 23.5A)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from channelflow.dataset import CertifiedDataset, Label, Row, WalkForwardFolds, certify

#: What a test asks for when it needs a dataset training will accept.
Certify = Callable[[list[Row]], CertifiedDataset]

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND


def _row(index: int, *, features: dict[str, float], label_class: str) -> Row:
    as_of_ns = index * SECOND
    horizon_end_ns = as_of_ns + HORIZON_NS
    return Row(
        entity="BTCUSDT",
        as_of_ns=as_of_ns,
        features=features,
        source_max_event_ns=as_of_ns,
        label=Label(
            label_class=label_class,  # type: ignore[arg-type]
            horizon_end_ns=horizon_end_ns,
            available_ns=horizon_end_ns,
        ),
    )


@pytest.fixture
def signal_rows() -> list[Row]:
    """A target a linear model can learn: `slope` decides the turn.

    Not because the market is like this, but because a baseline that cannot find
    a signal placed directly in front of it cannot be trusted to report the
    absence of one.
    """
    rows = []
    for index in range(120):
        slope = 1.0 if index % 2 == 0 else -1.0
        rows.append(
            _row(
                index,
                # The drift makes every row's feature vector distinct. Without
                # it `require_disjoint` sees a repeated vector as a shared row
                # and refuses a split that is genuinely disjoint in time.
                features={"slope": slope + index * 1e-6, "curvature": float(index % 3) - 1.0},
                label_class="MAX" if slope > 0 else "NO_TURN",
            )
        )
    return rows


@pytest.fixture
def signal_free_rows() -> list[Row]:
    """The same shape with the label detached from the features.

    The label alternates on a period of 3 and the features on a period of 2 and
    5, so no function of the features predicts it better than the base rate.
    """
    rows = []
    for index in range(120):
        rows.append(
            _row(
                index,
                features={
                    "slope": float(index % 2) + index * 1e-6,
                    "curvature": float(index % 5),
                },
                label_class="MAX" if index % 3 == 0 else "NO_TURN",
            )
        )
    return rows


@pytest.fixture
def certified() -> Certify:
    """Rows, folded and passed through the leakage checks.

    REQ-US-007's gate: training takes a certificate, so a test that fits a model
    builds one the same way a caller does. Certifying here rather than stubbing
    it also means these fixtures are checked -- a fixture with a leak in it
    would fail loudly rather than quietly train something.
    """

    def build(rows: list[Row]) -> CertifiedDataset:
        folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows)
        return certify(rows, folds)

    return build
