"""Point-in-time reads at the storage boundary.

REQ-STORE-001, PRD §24.1's invariant `source_max_event_time <= as_of_time`,
Constitution Principle I.
"""

from __future__ import annotations

import pytest

from channelflow.lakehouse import IcebergTable, NoEventTime

from .conftest import SECOND, trade


@pytest.mark.trace("REQ-STORE-001")
def test_a_point_in_time_read_returns_nothing_later_than_the_instant(trades: IcebergTable) -> None:
    """Principle I at the boundary where data leaves storage. A read that
    returned a later row would hand a feature something that had not happened,
    and every leakage check upstream would already have passed."""
    trades.append([trade(1), trade(2), trade(3), trade(4)])

    rows = trades.read(as_of_ns=2 * SECOND)

    assert rows.num_rows == 2
    assert max(rows["event_time_ns"].to_pylist()) <= 2 * SECOND


@pytest.mark.trace("REQ-STORE-001")
def test_the_instant_itself_is_included(trades: IcebergTable) -> None:
    """§24.1's invariant is `<=`, not `<`. A row whose event time is exactly the
    as-of instant was available at that instant."""
    trades.append([trade(1), trade(2)])

    assert trades.read(as_of_ns=2 * SECOND).num_rows == 2
    assert trades.read(as_of_ns=2 * SECOND - 1).num_rows == 1


@pytest.mark.trace("REQ-STORE-001")
def test_a_point_in_time_read_before_anything_happened_is_empty_rather_than_wrong(
    trades: IcebergTable,
) -> None:
    trades.append([trade(5)])

    assert trades.read(as_of_ns=1).num_rows == 0


@pytest.mark.trace("REQ-STORE-001")
def test_a_table_with_no_event_time_refuses_a_point_in_time_read(config: IcebergTable) -> None:
    """Returning everything would answer a different question in a way the
    caller could not detect: the rows would look like a correct as-of result and
    would include whatever arrived later."""
    config.append([{"key": "tick", "value": "0.01"}])

    with pytest.raises(NoEventTime, match="different question"):
        config.read(as_of_ns=1)


@pytest.mark.trace("REQ-STORE-001")
def test_a_point_in_time_read_composes_with_a_snapshot(trades: IcebergTable) -> None:
    """The two bounds are different questions and both have to hold at once:
    which commit, and which instant within it."""
    trades.append([trade(1), trade(2)])
    trades.append([trade(3), trade(4)])

    assert trades.read(snapshot_id=1, as_of_ns=4 * SECOND).num_rows == 2
    assert trades.read(snapshot_id=2, as_of_ns=4 * SECOND).num_rows == 4
    assert trades.read(snapshot_id=2, as_of_ns=2 * SECOND).num_rows == 2
