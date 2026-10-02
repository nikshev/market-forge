"""`build_daemon`: where configuration, registry, connector and archive meet (REQ-WP-078).

# @trace: REQ-WP-078

Every defect of REQ-WP-078 had a passing test beside it, because the tests exercised
the parts and the faults were in the joins. This file drives the join itself: the
daemon is built the way the deployment builds it, from the archive URI the compose
file gives an ingest service, and what it produced is read back.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from channelflow.pipeline.archive import LocalObjectStore
from channelflow.pipeline.ingest import IngestDaemon
from channelflow.pipeline.ingest_main import build_daemon, ingest_settings_from_env
from channelflow.settings import MissingConfiguration

ROOT = Path(__file__).resolve().parents[3]
NOW = 1_790_000_000_000_000_000

VENUES = [("binance", "BTCUSDT"), ("bybit", "BTCUSDT"), ("okx", "BTC-USDT-SWAP")]


def _deployment_archive_uri() -> str:
    """What compose gives an ingest service, with the bucket `.env.example` names.

    Read from the file and not copied here: a literal in this test would let the
    compose value drift away from what is tested.
    """
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    uri = compose["services"]["ingest-binance"]["environment"]["CHANNELFLOW_ARCHIVE_URI"]
    match = re.search(r"^MINIO_BUCKET=(.+)$", (ROOT / ".env.example").read_text(), re.M)
    assert match, ".env.example names no MINIO_BUCKET"
    return str(uri).replace("${MINIO_BUCKET}", match.group(1).strip())


def _build(venue: str, symbol: str, tmp_path: Path, store: LocalObjectStore) -> IngestDaemon:
    settings = ingest_settings_from_env(
        {
            "CHANNELFLOW_INGEST_SYMBOLS": symbol,
            "CHANNELFLOW_ARCHIVE_URI": _deployment_archive_uri(),
        }
    )
    return build_daemon(
        symbol=symbol,
        settings=settings,
        store=store,
        catalog_uri=f"sqlite:///{tmp_path}/catalog.db",
        warehouse=str(tmp_path / "warehouse"),
        storage={},
        venue=venue,
    )


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "symbol"), VENUES)
def test_the_key_the_wiring_builds_names_the_venue_once_under_raw_cex(
    venue: str, symbol: str, tmp_path: Path
) -> None:
    """The key as a string, because this test's whole job is the prefix the wiring builds.

    Before: `binance/raw/cex/binance/2026/...` -- the venue prefixed by `build_daemon`
    and appended again by `key_for`, at the bucket root where no reader looks.
    """
    bucket = tmp_path / "bucket"
    daemon = _build(venue, symbol, tmp_path, LocalObjectStore(root=bucket))

    daemon.archive.add(received_at_ns=NOW, frame="{}")
    assert daemon.archive.flush() is not None

    keys = [p.relative_to(bucket).as_posix() for p in bucket.rglob("*.jsonl.gz")]
    assert len(keys) == 1
    parts = keys[0].split("/")
    assert parts[:3] == ["raw", "cex", venue], keys[0]
    assert parts[3] == symbol, keys[0]
    assert parts.count(venue) == 1, keys[0]


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("venue", ["binance", "bybit"])
def test_a_lower_case_symbol_is_refused_where_the_spelling_would_split_an_instrument(
    venue: str, tmp_path: Path
) -> None:
    """The key uses the symbol as configured and the migration writes upper case. A
    deployment configured `btcusdt` would put one instrument in two directories."""
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_INGEST_SYMBOLS"):
        _build(venue, "btcusdt", tmp_path, LocalObjectStore(root=tmp_path / "bucket"))


@pytest.mark.trace("REQ-WP-078")
def test_okx_instruments_are_accepted_as_written(tmp_path: Path) -> None:
    daemon = _build("okx", "BTC-USDT-SWAP", tmp_path, LocalObjectStore(root=tmp_path / "bucket"))

    assert daemon.venue == "okx"


# --- the connector the daemon built -------------------------------------------------
#
# OKX could not connect for six days. The daemon opened `wss://ws.okx.com/api/v5/market`,
# a REST path prefix that answers `HTTP 404`, and then -- at the right URL -- subscribed
# with `instId = "trades.BTC-USDT-SWAP"`, which OKX answers with "Subscribe failed". Both
# were reproduced live. The tests read `_url` and `_subscribe_msg` off the connector the
# daemon **built**, because a test of a helper called with convenient arguments could not
# see either.


@pytest.mark.trace("REQ-WP-078")
def test_okx_opens_the_public_endpoint_and_subscribes_with_the_instrument_as_okx_names_it(
    tmp_path: Path,
) -> None:
    daemon = _build("okx", "BTC-USDT-SWAP", tmp_path, LocalObjectStore(root=tmp_path / "bucket"))

    assert daemon.connector._url == "wss://ws.okx.com:8443/ws/v5/public"
    assert json.loads(daemon.connector._subscribe_msg) == {
        "op": "subscribe",
        "args": [{"channel": "trades", "instId": "BTC-USDT-SWAP"}],
    }


@pytest.mark.trace("REQ-WP-078")
def test_bybit_opens_its_linear_endpoint_and_subscribes_to_the_public_trade_topic(
    tmp_path: Path,
) -> None:
    daemon = _build("bybit", "BTCUSDT", tmp_path, LocalObjectStore(root=tmp_path / "bucket"))

    assert daemon.connector._url == "wss://stream.bybit.com/v5/public/linear"
    assert json.loads(daemon.connector._subscribe_msg) == {
        "op": "subscribe",
        "args": ["publicTrade.BTCUSDT"],
    }


@pytest.mark.trace("REQ-WP-078")
def test_binance_subscribes_through_its_url_and_sends_nothing(tmp_path: Path) -> None:
    daemon = _build("binance", "BTCUSDT", tmp_path, LocalObjectStore(root=tmp_path / "bucket"))

    url = daemon.connector._transport.url_for(("btcusdt@aggTrade",))
    assert url == "wss://stream.binance.com:9443/stream?streams=btcusdt@aggTrade"


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "symbol"), VENUES)
def test_the_session_runs_the_registrys_policy_for_the_venue(
    venue: str, symbol: str, tmp_path: Path
) -> None:
    """The daemon's silence threshold was 48 hours because it read a policy the registry
    held and the measured one did not."""
    from channelflow.connectors.venue import VENUE_REGISTRY

    daemon = _build(venue, symbol, tmp_path, LocalObjectStore(root=tmp_path / "bucket"))

    assert daemon.session.policy == VENUE_REGISTRY[venue].policy
    assert daemon.session.policy.max_silence_ns == 60 * 1_000_000_000


@pytest.mark.trace("REQ-WP-078")
def test_the_silence_limit_is_configuration_and_reaches_the_session(tmp_path: Path) -> None:
    settings = ingest_settings_from_env(
        {
            "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
            "CHANNELFLOW_ARCHIVE_URI": _deployment_archive_uri(),
            "CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS": "90",
        }
    )

    daemon = build_daemon(
        symbol="BTCUSDT",
        settings=settings,
        store=LocalObjectStore(root=tmp_path / "bucket"),
        catalog_uri=f"sqlite:///{tmp_path}/catalog.db",
        warehouse=str(tmp_path / "warehouse"),
        storage={},
        venue="bybit",
    )

    assert daemon.session.policy.max_silence_ns == 90 * 1_000_000_000


@pytest.mark.trace("REQ-WP-078")
def test_a_silence_limit_the_policy_cannot_hold_is_refused_naming_the_variable(
    tmp_path: Path,
) -> None:
    """Bybit pings every 20 s; a limit of 10 s would reconnect a healthy quiet connection
    between two pongs."""
    settings = ingest_settings_from_env(
        {
            "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
            "CHANNELFLOW_ARCHIVE_URI": _deployment_archive_uri(),
            "CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS": "10",
        }
    )

    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS"):
        build_daemon(
            symbol="BTCUSDT",
            settings=settings,
            store=LocalObjectStore(root=tmp_path / "bucket"),
            catalog_uri=f"sqlite:///{tmp_path}/catalog.db",
            warehouse=str(tmp_path / "warehouse"),
            storage={},
            venue="bybit",
        )
