"""Each ingest process registers the market it ingests (REQ-WP-081).

`GET /api/v1/markets` answered `{"markets":[]}` with five ingest services delivering bars, because
the list
is read from the `markets` table and nothing running wrote to it. These tests are about the writer:
that it
writes one row with the venue's type and no invented rules, that it is idempotent, that it does not
overwrite what is held, that five of them at once end with five rows, and -- through `main` -- that
a
failure to register costs the process nothing.
"""

from __future__ import annotations

import logging
import threading
from decimal import Decimal
from typing import Any

import pytest

from channelflow.api.lakehouse_repository import LakehouseRepository
from channelflow.domain.instrument import Instrument
from channelflow.lakehouse import Catalog
from channelflow.pipeline import ingest_main
from channelflow.pipeline.market_registration import (
    register_market,
    register_own_market,
    register_softly,
)
from channelflow.tables import features as features_table


def _rows(catalog: Catalog) -> list[dict[str, Any]]:
    return features_table.markets_table_for(catalog).read().to_pylist()


def _keys(catalog: Catalog) -> list[tuple[str, str]]:
    return sorted((r["venue"], r["symbol"]) for r in _rows(catalog))


# --- the row -------------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-081")
def test_the_row_is_exactly_what_the_repository_writes_for_a_market_without_rules(
    catalog: Catalog,
) -> None:
    """One definition of 'a market with no rules', used by both."""
    LakehouseRepository(catalog=catalog).add_market(venue="v", symbol="S", market_type="perp")

    stored = [{k: str(v) for k, v in row.items()} for row in _rows(catalog)]
    expected = [{k: str(v) for k, v in features_table.unruled_market_row("v", "S", "perp").items()}]
    assert stored == expected  # decimal columns read back as text, so compare as text


@pytest.mark.trace("REQ-WP-081")
def test_registering_writes_one_row_that_reads_back_with_no_instrument(catalog: Catalog) -> None:
    added = register_market(catalog, venue="bybit", symbol="BTCUSDT", market_type="perp")

    assert added is True
    [row] = _rows(catalog)
    assert (row["venue"], row["symbol"], row["market_type"]) == ("bybit", "BTCUSDT", "perp")
    assert features_table.instrument_from_row(row) is None, "no rules were invented"


# --- idempotence ---------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-081")
def test_registering_twice_adds_nothing(catalog: Catalog) -> None:
    register_market(catalog, venue="okx", symbol="BTC-USDT-SWAP", market_type="perp")

    again = register_market(catalog, venue="okx", symbol="BTC-USDT-SWAP", market_type="perp")

    assert again is False
    assert len(_rows(catalog)) == 1


@pytest.mark.trace("REQ-WP-081")
def test_ten_starts_leave_one_row_for_the_key(catalog: Catalog) -> None:
    """SC-002."""
    for _ in range(10):
        register_market(catalog, venue="binance", symbol="ETHUSDT", market_type="spot")

    assert _keys(catalog) == [("binance", "ETHUSDT")]


@pytest.mark.trace("REQ-WP-081")
def test_a_key_held_with_trading_rules_is_recognised_and_not_overwritten(catalog: Catalog) -> None:
    held = Instrument(
        venue="binance",
        symbol="BTCUSDT",
        market_type="spot",
        base_asset="BTC",
        quote_asset="USDT",
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.00001"),
        min_notional=Decimal("5"),
        contract_size=None,
        status="TRADING",
    )
    LakehouseRepository(catalog=catalog).add_market(
        venue="binance", symbol="BTCUSDT", market_type="spot", instrument=held
    )

    added = register_market(catalog, venue="binance", symbol="BTCUSDT", market_type="spot")

    assert added is False
    [row] = _rows(catalog)
    assert Decimal(row["tick_size"]) == Decimal("0.01"), "the rules that were there are still there"


@pytest.mark.trace("REQ-WP-081")
def test_five_keys_registered_at_once_end_with_five_rows(catalog: Catalog) -> None:
    keys = [
        ("binance", "BTCUSDT", "spot"),
        ("binance", "ETHUSDT", "spot"),
        ("binance", "SOLUSDT", "spot"),
        ("bybit", "BTCUSDT", "perp"),
        ("okx", "BTC-USDT-SWAP", "perp"),
    ]
    errors: list[BaseException] = []

    def go(venue: str, symbol: str, market_type: str) -> None:
        try:
            register_market(catalog, venue=venue, symbol=symbol, market_type=market_type)
        except BaseException as error:  # noqa: BLE001 -- any failure fails the test below
            errors.append(error)

    threads = [threading.Thread(target=go, args=key) for key in keys]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert _keys(catalog) == sorted((v, s) for v, s, _ in keys)


# --- failure is soft -----------------------------------------------------------------------


class _FakeDaemon:
    def __init__(self) -> None:
        self.ran = 0

    def run(self) -> None:
        self.ran += 1


def _env(monkeypatch: pytest.MonkeyPatch, *, venue: str, symbol: str) -> None:
    monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", "sqlite:///unused.db")
    monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", "/tmp/unused")
    monkeypatch.setenv("CHANNELFLOW_INGEST_VENUE", venue)
    monkeypatch.setenv("CHANNELFLOW_INGEST_SYMBOLS", symbol)
    monkeypatch.setenv("CHANNELFLOW_ARCHIVE_URI", "file:///tmp/unused-archive")


def _run_main(monkeypatch: pytest.MonkeyPatch, daemon: _FakeDaemon, **patched: Any) -> None:
    monkeypatch.setattr(ingest_main, "build_daemon", lambda **_: daemon)
    monkeypatch.setattr(ingest_main, "object_store_for", lambda *a, **k: object())
    for name, value in patched.items():
        monkeypatch.setattr(ingest_main, name, value)
    assert ingest_main.main([]) == 0


@pytest.mark.trace("REQ-WP-081")
def test_a_failing_registration_is_one_warning_naming_venue_and_symbol_and_ingest_runs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """SC-003, and FR-006: ingest is the product, the list is not; registration is tried once."""
    _env(monkeypatch, venue="bybit", symbol="BTCUSDT")
    attempts: list[int] = []

    def failing(*args: Any, **kwargs: Any) -> bool:
        attempts.append(1)
        raise RuntimeError("the catalog said no")

    daemon = _FakeDaemon()
    caplog.set_level(logging.INFO)
    monkeypatch.setattr("channelflow.pipeline.market_registration.register_market", failing)
    monkeypatch.setattr(
        "channelflow.pipeline.market_registration.open_catalog", lambda **_: object()
    )

    _run_main(monkeypatch, daemon)

    assert daemon.ran == 1, "a failure to register must not stop ingest"
    assert len(attempts) == 1, "tried once, not in a loop"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "bybit" in warnings[0].getMessage() and "BTCUSDT" in warnings[0].getMessage()


@pytest.mark.trace("REQ-WP-081")
def test_an_instrument_okx_does_not_recognise_is_a_warning_and_ingest_runs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _env(monkeypatch, venue="okx", symbol="BTC-USDT-240329")
    daemon = _FakeDaemon()
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        "channelflow.pipeline.market_registration.open_catalog", lambda **_: object()
    )

    _run_main(monkeypatch, daemon)

    assert daemon.ran == 1
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "okx" in warnings[0] and "BTC-USDT-240329" in warnings[0]


@pytest.mark.trace("REQ-WP-081")
def test_register_softly_reports_what_it_did_and_never_raises(catalog: Catalog) -> None:
    assert register_softly(catalog, venue="bybit", symbol="BTCUSDT") is True
    assert register_softly(catalog, venue="bybit", symbol="BTCUSDT") is False


# --- found by the mutation sweep: three behaviours the first tests did not pin ---------------


@pytest.mark.trace("REQ-WP-081")
@pytest.mark.parametrize(
    ("venue", "symbol", "expected"),
    [
        ("binance", "BTCUSDT", "spot"),
        ("bybit", "BTCUSDT", "perp"),
        ("okx", "BTC-USDT-SWAP", "perp"),
        ("okx", "BTC-USDT", "spot"),
    ],
)
def test_the_row_carries_the_type_the_registry_gives_that_venue(
    catalog: Catalog, venue: str, symbol: str, expected: str
) -> None:
    """Written after the sweep: with every first test on a perpetual, a registration that wrote
    `perp` for everything -- the convenient and false answer -- still passed."""
    register_softly(catalog, venue=venue, symbol=symbol)

    [row] = _rows(catalog)
    assert row["market_type"] == expected


@pytest.mark.trace("REQ-WP-081")
def test_two_symbols_of_one_venue_are_both_registered(catalog: Catalog) -> None:
    """The key is the venue **and** the symbol: Binance has three daemons."""
    register_market(catalog, venue="binance", symbol="BTCUSDT", market_type="spot")
    register_market(catalog, venue="binance", symbol="ETHUSDT", market_type="spot")

    assert _keys(catalog) == [("binance", "BTCUSDT"), ("binance", "ETHUSDT")]


@pytest.mark.trace("REQ-WP-081")
def test_an_unreachable_catalog_is_the_same_soft_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def unreachable(**_: Any) -> Any:
        raise ConnectionError("the database is not there")

    monkeypatch.setattr("channelflow.pipeline.market_registration.open_catalog", unreachable)
    caplog.set_level(logging.INFO)

    got = register_own_market(
        venue="okx", symbol="BTC-USDT-SWAP", catalog_uri="x", warehouse="y", storage={}
    )

    assert got is None
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "okx" in warnings[0] and "BTC-USDT-SWAP" in warnings[0]
