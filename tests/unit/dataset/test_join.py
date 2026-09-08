"""PRD section 24.2's training join (REQ-WP-017, REQ-BIAS-004).

Labels may use future data. Features may not.
"""

from __future__ import annotations

import pytest

from channelflow.dataset import (
    AmbiguousSnapshot,
    DropReason,
    FeatureSnapshot,
    Label,
    as_of_snapshot,
    build_rows,
)

from .conftest import BASE_NS, ENTITY, MINUTE_NS, snapshot


def label_at(at: int, horizon: int = 5) -> Label:
    return Label(
        label_class="NO_TURN",
        horizon_end_ns=BASE_NS + (at + horizon) * MINUTE_NS,
        available_ns=BASE_NS + (at + horizon) * MINUTE_NS,
    )


@pytest.mark.trace("REQ-WP-017")
def test_only_snapshots_at_or_before_t_are_joined() -> None:
    """SC-001, FR-001. The whole feature in one assertion."""
    snapshots = [snapshot(at=3, value=0.3), snapshot(at=7, value=0.7)]

    chosen = as_of_snapshot(
        snapshots, entity=ENTITY, feature_name="qi_l1", at_ns=BASE_NS + 5 * MINUTE_NS
    )

    assert chosen is not None
    assert chosen.value == 0.3, "the snapshot from minute 7 is in the future at minute 5"


@pytest.mark.trace("REQ-WP-017")
def test_the_most_recent_qualifying_snapshot_is_used() -> None:
    """FR-003. A join taking the first match would use stale data everywhere."""
    snapshots = [snapshot(at=1, value=0.1), snapshot(at=3, value=0.3), snapshot(at=9, value=0.9)]

    chosen = as_of_snapshot(
        snapshots, entity=ENTITY, feature_name="qi_l1", at_ns=BASE_NS + 5 * MINUTE_NS
    )

    assert chosen is not None and chosen.value == 0.3


@pytest.mark.trace("REQ-WP-017")
def test_a_snapshot_that_saw_the_future_cannot_be_constructed() -> None:
    """SC-002, FR-002. PRD section 24.1's invariant:
    `source_max_event_time <= as_of_time`.

    Enforced at construction rather than checked later: a snapshot computed
    with hindsight and stamped with an old date is the one kind of leak no
    downstream check can detect, because by then it looks like any other row.
    """
    with pytest.raises(ValueError, match="section 24.1"):
        FeatureSnapshot(
            entity=ENTITY,
            as_of_ns=BASE_NS,
            feature_name="qi_l1",
            feature_version=1,
            value=0.5,
            source_max_event_ns=BASE_NS + 10 * MINUTE_NS,
        )


@pytest.mark.trace("REQ-WP-017")
def test_a_missing_snapshot_drops_the_row_and_is_counted() -> None:
    """FR-004. Never forward-filled from a later value -- that is the leak, and
    it would be invisible in the row."""
    report = build_rows(
        entity=ENTITY,
        as_of_times=[BASE_NS + i * MINUTE_NS for i in (2, 8)],
        snapshots=[snapshot(at=5, value=0.5)],
        feature_names=["qi_l1"],
        labels={BASE_NS + i * MINUTE_NS: label_at(i) for i in (2, 8)},
    )

    assert report.built == 1, "minute 2 has no snapshot at or before it"
    assert report.dropped[DropReason.NO_SNAPSHOT] == 1
    assert report.rows[0].as_of_ns == BASE_NS + 8 * MINUTE_NS


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-004")
def test_a_feature_from_an_unfinalized_bar_is_refused() -> None:
    """FR-005, PRD section 41 rule 4.

    The PRD says "no using final daily high/low before daily close". This is
    the same defect at any timeframe: a 15-minute bar read before it closed can
    still change, and a feature derived from it is a guess dressed as data.
    """
    report = build_rows(
        entity=ENTITY,
        as_of_times=[BASE_NS + 5 * MINUTE_NS],
        snapshots=[snapshot(at=5, finalized=False)],
        feature_names=["qi_l1"],
        labels={BASE_NS + 5 * MINUTE_NS: label_at(5)},
    )

    assert report.built == 0
    assert report.dropped[DropReason.UNFINALIZED_BAR] == 1


@pytest.mark.trace("REQ-WP-017")
def test_two_indistinguishable_snapshots_are_refused() -> None:
    """The spec's first edge case.

    Same as-of time and same source event: nothing in the data breaks the tie,
    and picking arbitrarily would make the dataset depend on list order.
    """
    duplicates = [snapshot(at=5, value=0.1), snapshot(at=5, value=0.9)]

    with pytest.raises(AmbiguousSnapshot, match="indistinguishable"):
        as_of_snapshot(
            duplicates, entity=ENTITY, feature_name="qi_l1", at_ns=BASE_NS + 5 * MINUTE_NS
        )


@pytest.mark.trace("REQ-WP-017")
def test_a_tie_on_as_of_is_broken_by_the_later_source_event() -> None:
    """The freshest view of the same instant wins, which is a rule the data
    can express -- unlike the case above."""
    snapshots = [
        snapshot(at=5, value=0.1, source_at=3),
        snapshot(at=5, value=0.9, source_at=5),
    ]

    chosen = as_of_snapshot(
        snapshots, entity=ENTITY, feature_name="qi_l1", at_ns=BASE_NS + 5 * MINUTE_NS
    )

    assert chosen is not None and chosen.value == 0.9


@pytest.mark.trace("REQ-WP-017")
def test_every_drop_reason_is_counted_separately() -> None:
    """A build that returned an empty list for five different reasons would be
    unreadable: "no data here" and "our dataset is contaminated" are not the
    same result."""
    report = build_rows(
        entity=ENTITY,
        as_of_times=[BASE_NS + i * MINUTE_NS for i in (1, 5, 9)],
        snapshots=[snapshot(at=5, finalized=False), snapshot(at=9)],
        feature_names=["qi_l1"],
        labels={BASE_NS + i * MINUTE_NS: label_at(i) for i in (1, 5)},
    )

    assert report.dropped[DropReason.NO_SNAPSHOT] == 1, "minute 1"
    assert report.dropped[DropReason.UNFINALIZED_BAR] == 1, "minute 5"
    assert report.dropped[DropReason.NO_LABEL] == 1, "minute 9"
    assert report.considered == 3
