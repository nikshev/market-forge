"""PRD section 42's point-in-time universe (REQ-BIAS-007, REQ-BIAS-008).

Rules 7 and 8 of PRD section 41 are the same mistake seen twice: asking what is
tradeable now and pretending it was tradeable then. Both are avoided by never
having a "now" to ask about.
"""

from __future__ import annotations

import pytest

from channelflow.dataset import DropReason, Listing, PointInTimeUniverse, build_rows

from .conftest import BASE_NS, ENTITY, MINUTE_NS, snapshot
from .test_join import label_at


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-007")
def test_a_symbol_listed_later_is_absent_earlier() -> None:
    """SC-008, FR-014. The survivorship mistake, in its simplest form."""
    universe = PointInTimeUniverse(listings=[Listing(entity="NEW", listed_ns=at(50))])

    assert universe.at(at(10)) == set()
    assert universe.at(at(50)) == {"NEW"}
    assert universe.at(at(90)) == {"NEW"}


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-007")
def test_a_delisted_symbol_is_absent_afterwards() -> None:
    """FR-014. The other half: a backtest over today's listings never sees what
    failed, and every strategy looks better for it."""
    universe = PointInTimeUniverse(
        listings=[Listing(entity="GONE", listed_ns=at(0), delisted_ns=at(40))]
    )

    assert universe.at(at(20)) == {"GONE"}
    assert universe.at(at(40)) == set()
    assert universe.at(at(60)) == set()


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-008")
def test_eligibility_uses_only_trailing_observations() -> None:
    """FR-014, PRD section 41 rule 8.

    The volume that makes a symbol eligible must be volume already observed. A
    universe built from the whole history's volume is today's top-volume list
    wearing a date.
    """
    universe = PointInTimeUniverse(
        listings=[Listing(entity="THIN", listed_ns=at(0))],
        volume_observations={"THIN": [(at(10), 5.0), (at(60), 5000.0)]},
        min_trailing_volume=1000.0,
    )

    assert universe.at(at(30)) == set(), "only 5.0 had been observed by minute 30"
    assert universe.at(at(70)) == {"THIN"}


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-008")
def test_rows_outside_the_universe_are_dropped_and_counted() -> None:
    """FR-015. The universe is a filter on which rows may exist at all."""
    universe = PointInTimeUniverse(listings=[Listing(entity=ENTITY, listed_ns=at(20))])

    report = build_rows(
        entity=ENTITY,
        as_of_times=[at(5), at(30)],
        snapshots=[snapshot(at=1), snapshot(at=25)],
        feature_names=["qi_l1"],
        labels={at(5): label_at(5), at(30): label_at(30)},
        universe=universe,
    )

    assert report.built == 1
    assert report.dropped[DropReason.NOT_IN_UNIVERSE] == 1


@pytest.mark.trace("REQ-WP-017")
def test_an_empty_universe_drops_everything_visibly() -> None:
    """The spec's fifth edge case: the exclusion is counted, so an empty result
    is distinguishable from a filter that matched nothing by accident."""
    report = build_rows(
        entity=ENTITY,
        as_of_times=[at(5)],
        snapshots=[snapshot(at=1)],
        feature_names=["qi_l1"],
        labels={at(5): label_at(5)},
        universe=PointInTimeUniverse(listings=[]),
    )

    assert report.built == 0
    assert report.dropped[DropReason.NOT_IN_UNIVERSE] == 1
    assert report.considered == 1
