"""The API serves the volume profile from the stored price bins (REQ-WP-089)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from channelflow.api import InMemoryRepository, create_app
from channelflow.volume.bins import BinBlock, BinRow

BLOCK_NS = 300_000_000_000
HOUR_NS = 3_600_000_000_000
BASE = 1_788_838_800_000_000_000 // BLOCK_NS * BLOCK_NS


def block(i: int, *, width: str = "10", symbol: str = "BTCUSDT") -> BinBlock:
    return BinBlock(
        venue="binance",
        symbol=symbol,
        block_open_time_ns=BASE + i * BLOCK_NS,
        block_ns=BLOCK_NS,
        bin_width=Decimal(width),
        bins=(
            BinRow(index=10, buy=Decimal("2"), sell=Decimal("1"), unknown=Decimal("0"), trades=3),
            BinRow(index=11, buy=Decimal("4"), sell=Decimal("5"), unknown=Decimal("6"), trades=3),
        ),
    )


def client(blocks) -> TestClient:
    repo = InMemoryRepository()
    for b in blocks:
        repo.add_bin_block(b)
    return TestClient(create_app(repository=repo))


def get(c: TestClient, **params):
    return c.get(
        "/api/v1/volume-profile",
        params={"venue": "binance", "symbol": "BTCUSDT", "window": "24h", **params},
    )


@pytest.mark.trace("REQ-WP-089")
def test_the_profile_carries_its_bins_poc_value_area_instant_width_and_coverage() -> None:
    body = get(client([block(i) for i in range(6)])).json()

    assert body["venue"] == "binance" and body["symbol"] == "BTCUSDT" and body["window"] == "24h"
    assert body["bin_width"] == "10"
    assert [b["low"] for b in body["bins"]] == ["100", "110"]
    first = body["bins"][0]
    assert (first["buy"], first["sell"], first["unknown"], first["trades"]) == ("12", "6", "0", 18)
    assert body["bins"][1]["buy"] == "24" and body["bins"][1]["unknown"] == "36"
    assert body["poc_index"] == 1
    assert {"value_area_low", "value_area_high", "poc_tie", "value_area_is_whole_profile"} <= set(
        body
    )
    assert body["as_of_ns"] == str(BASE + 6 * BLOCK_NS)


@pytest.mark.trace("REQ-WP-089")
def test_a_profile_from_three_hours_of_data_says_so_and_is_not_complete() -> None:
    """SC-004: 36 blocks of five minutes are three hours; a 24h window is not covered."""
    body = get(client([block(i) for i in range(36)])).json()

    assert body["covered_ns"] == 3 * HOUR_NS
    assert body["covers_from_ns"] == str(BASE)
    assert body["window_ns"] == 24 * HOUR_NS
    assert body["complete"] is False


@pytest.mark.trace("REQ-WP-089")
def test_a_window_the_data_fills_is_complete_and_uses_only_the_window() -> None:
    blocks = [block(i) for i in range(2 * 12 * 5)]  # ten hours of data
    body = get(client(blocks), window="4h").json()

    assert body["complete"] is True
    assert body["covered_ns"] == 4 * HOUR_NS
    assert body["bins"][0]["trades"] == 3 * 48


@pytest.mark.trace("REQ-WP-089")
def test_a_profile_as_of_an_instant_uses_only_blocks_closed_by_then() -> None:
    """SC-003: later blocks change nothing."""
    c = client([block(i) for i in range(10)])
    early = get(c, at_ns=BASE + 4 * BLOCK_NS).json()

    c.app.state.repository.add_bin_block(block(10))  # type: ignore[attr-defined]
    again = get(c, at_ns=BASE + 4 * BLOCK_NS).json()

    assert early == again
    assert early["as_of_ns"] == str(BASE + 4 * BLOCK_NS)
    assert early["bins"][0]["trades"] == 12


@pytest.mark.trace("REQ-WP-089")
def test_without_an_instant_the_latest_closed_block_is_the_instant() -> None:
    body = get(client([block(i) for i in range(3)])).json()

    assert body["as_of_ns"] == str(BASE + 3 * BLOCK_NS)


@pytest.mark.trace("REQ-WP-089")
def test_rows_of_another_width_are_left_out_and_counted() -> None:
    body = get(client([block(0, width="10"), block(1, width="20")])).json()

    assert body["bin_width"] == "20"
    assert body["left_out_rows"] == 2


@pytest.mark.trace("REQ-WP-089")
def test_no_bins_is_a_404_with_a_reason_never_an_empty_profile() -> None:
    response = get(client([block(0, symbol="ETHUSDT")]))

    assert response.status_code == 404
    assert "no price bins" in response.json()["detail"]


@pytest.mark.trace("REQ-WP-089")
@pytest.mark.parametrize("window", ["5m", "1d", "24", ""])
def test_a_window_other_than_4h_24h_or_7d_is_refused(window: str) -> None:
    assert get(client([block(0)]), window=window).status_code == 422


@pytest.mark.trace("REQ-WP-089")
def test_the_lakehouse_repository_and_the_in_memory_one_serve_the_same_profile(catalog) -> None:
    from channelflow.api.lakehouse_repository import LakehouseRepository
    from channelflow.tables import volume_bins

    blocks = [block(i) for i in range(8)] + [block(8, width="20")]
    sink = volume_bins.BinSink(table=volume_bins.table_for(catalog))
    for b in blocks:
        sink(b)
    sink.flush()
    memory = client(blocks)
    lake = TestClient(create_app(repository=LakehouseRepository(catalog=catalog)))

    for params in ({}, {"at_ns": BASE + 5 * BLOCK_NS}, {"window": "4h"}):
        assert get(lake, **params).json() == get(memory, **params).json()
