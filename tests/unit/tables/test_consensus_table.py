"""The consensus table: one row per (asset, market_type, bar close) (REQ-WP-091)."""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa
import pytest

from channelflow.tables import consensus

BAR_CLOSE_NS = 1_788_838_800_000_000_000


def agreed() -> consensus.Consensus:
    """Three spot venues contributing one bar's consensus."""
    return consensus.Consensus(
        asset="ETHUSDT",
        market_type="spot",
        bar_close_ns=BAR_CLOSE_NS,
        consensus_mid=Decimal("2400.15"),
        venue_count=3,
        refusal_reason="",
    )


@pytest.mark.trace("REQ-WP-091")
def test_the_table_is_named_consensus() -> None:
    assert consensus.TABLE_NAME == "consensus"


@pytest.mark.trace("REQ-WP-091")
def test_the_schema_is_exactly_the_six_columns_with_the_bar_close_as_event_time() -> None:
    assert [(c.name, c.type) for c in consensus.SCHEMA.columns] == [
        ("asset", "string"),
        ("market_type", "string"),
        # The bar's close is the event time: a consensus row is knowable only
        # once the bar has closed, so a point-in-time read as of an instant
        # inside the bar must not return it -- and the consensus itself may use
        # only quotes at or before this close (no look-ahead).
        ("bar_close_ns", "timestamp_ns"),
        ("consensus_mid", "decimal"),
        ("venue_count", "int64"),
        # Empty string means "no refusal"; the plane's optional strings are
        # written that way throughout (`tables/extrema.py`).
        ("refusal_reason", "string"),
    ]
    assert consensus.SCHEMA.event_time_column == "bar_close_ns"
    assert consensus.SCHEMA.arrow().field("bar_close_ns").type == pa.int64()


@pytest.mark.trace("REQ-WP-091")
def test_to_row_maps_the_consensus_in_the_schemas_own_column_order() -> None:
    row = consensus.to_row(agreed())

    assert row == {
        "asset": "ETHUSDT",
        "market_type": "spot",
        "bar_close_ns": BAR_CLOSE_NS,
        "consensus_mid": Decimal("2400.15"),
        "venue_count": 3,
        "refusal_reason": "",
    }


@pytest.mark.trace("REQ-WP-091")
def test_the_consensus_mid_is_decimal_and_never_float() -> None:
    row = consensus.to_row(agreed())

    assert isinstance(row["consensus_mid"], Decimal)
    assert not isinstance(row["consensus_mid"], float)


@pytest.mark.trace("REQ-WP-091")
def test_the_refusal_reason_is_a_column_and_empty_means_none() -> None:
    assert ("refusal_reason", "string") in [(c.name, c.type) for c in consensus.SCHEMA.columns]

    assert consensus.to_row(agreed())["refusal_reason"] == ""
    refused = consensus.Consensus(
        asset="ETHUSDT",
        market_type="perp",
        bar_close_ns=BAR_CLOSE_NS,
        consensus_mid=None,
        venue_count=1,
        refusal_reason="only 1 venue has a fresh mid",
    )
    assert consensus.to_row(refused)["refusal_reason"] == "only 1 venue has a fresh mid"


@pytest.mark.trace("REQ-WP-091")
def test_a_refused_bar_stores_the_reason_and_no_price() -> None:
    row = consensus.to_row(
        consensus.Consensus(
            asset="ETHUSDT",
            market_type="perp",
            bar_close_ns=BAR_CLOSE_NS,
            consensus_mid=None,
            venue_count=1,
            refusal_reason="only 1 venue has a fresh mid",
        )
    )

    # One row per (asset, market_type, bar close) either way, so the chart's
    # gap carries its reason -- and a refusal writes no price a reader could
    # mistake for one.
    assert row["venue_count"] == 1
    assert row["consensus_mid"] is None
