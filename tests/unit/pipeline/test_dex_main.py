"""The DEX collector's entrypoint reads its configuration strictly and resumes where it stopped
(REQ-WP-099)."""

from __future__ import annotations

import pytest

from channelflow.pipeline import dex_main as main
from channelflow.settings import MissingConfiguration

pytestmark = pytest.mark.trace("REQ-WP-099")


def test_the_defaults_are_the_public_node_and_the_collectors_port() -> None:
    settings = main.dex_settings_from_env({})

    assert settings.rpc_url == "https://rpc.hyperliquid.xyz/evm"
    assert settings.port == main.DEFAULT_PORT


def test_the_node_and_the_port_can_be_set_and_are_trimmed() -> None:
    settings = main.dex_settings_from_env(
        {"CHANNELFLOW_DEX_RPC_URL": " https://rpc.example/evm ", "CHANNELFLOW_DEX_PORT": "9300"}
    )

    assert settings.rpc_url == "https://rpc.example/evm"
    assert settings.port == 9300


@pytest.mark.parametrize("port", ["abc", "0", "70000", "-1"])
def test_a_bad_port_is_refused(port: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_DEX_PORT"):
        main.dex_settings_from_env({"CHANNELFLOW_DEX_PORT": port})


@pytest.mark.parametrize("url", ["rpc.example", "ftp://rpc.example", "javascript:1"])
def test_a_node_that_is_not_an_http_url_is_refused(url: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_DEX_RPC_URL"):
        main.dex_settings_from_env({"CHANNELFLOW_DEX_RPC_URL": url})


def test_the_collector_resumes_from_the_last_block_it_stored() -> None:
    rows = [
        {"chain_id": 999, "block_number": 100},
        {"chain_id": 999, "block_number": 250},
        {"chain_id": 1, "block_number": 9_999},  # another chain's: not ours
    ]

    assert main.last_stored_block(rows, chain_id=999) == 250


def test_an_empty_table_has_no_last_block() -> None:
    assert main.last_stored_block([], chain_id=999) is None
