"""Every service's log is capped, and the ingest services can be told how loud to be (REQ-WP-078).

# @trace: REQ-WP-078

Bybit's container log was 6.6 GB after six days, with no cap on it or on any other service.
A cap does not make a noisy service quiet -- that is the demotion of the lines at source --
but it is what stops the next noisy one filling a disk shared with other things.

The file is read as YAML, as data, so a service added later without a cap fails here on the
commit that adds it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"


def services() -> dict[str, dict]:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def uncapped(all_services: dict[str, dict]) -> list[str]:
    """Names of services with no `logging.options.max-size`, or an empty one."""
    return sorted(
        name
        for name, definition in all_services.items()
        if not str((definition.get("logging") or {}).get("options", {}).get("max-size", "")).strip()
    )


@pytest.mark.trace("REQ-WP-078")
def test_every_service_has_a_log_size_cap() -> None:
    assert uncapped(services()) == []


@pytest.mark.trace("REQ-WP-078")
def test_the_check_fails_for_a_service_without_one() -> None:
    """A guard that has never seen the thing it forbids guards nothing."""
    capped = {"logging": {"driver": "json-file", "options": {"max-size": "20m", "max-file": "3"}}}

    assert uncapped(
        {"ok": capped, "bare": {}, "empty": {"logging": {"options": {"max-size": ""}}}}
    ) == [
        "bare",
        "empty",
    ]


@pytest.mark.trace("REQ-WP-078")
def test_the_cap_is_configuration_with_a_default_and_keeps_a_few_files() -> None:
    options = services()["ingest-bybit"]["logging"]["options"]

    assert options["max-size"] == "${CHANNELFLOW_LOG_MAX_SIZE:-20m}"
    assert str(options["max-file"]) == "${CHANNELFLOW_LOG_MAX_FILE:-3}"


@pytest.mark.trace("REQ-WP-078")
def test_every_ingest_service_is_handed_the_silence_limit_and_the_log_level() -> None:
    """Compose forwards only the variables a service names. A setting added to `.env.example`
    and to the settings reader would otherwise be unreachable on the host -- configurable in
    the code and not in the deployment."""
    ingest = {name: d for name, d in services().items() if name.startswith("ingest-")}

    # Five before, the three OKX spot symbols (REQ-WP-098) and HYPE on two venues (REQ-WP-099).
    assert len(ingest) == 10
    for name, definition in ingest.items():
        environment = definition["environment"]
        assert "CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS" in environment, name
        assert "CHANNELFLOW_LOG_LEVEL" in environment, name


@pytest.mark.trace("REQ-WP-099")
def test_the_dex_collector_is_a_service_that_reports_its_own_health_and_holds_no_key() -> None:
    definition = services()["context-hyperevm"]

    assert "channelflow.pipeline.dex_main" in definition["command"]
    assert "healthcheck" in definition
    assert definition["restart"] == "unless-stopped"
    secrets = [k for k in definition["environment"] if "KEY" in k and "S3" not in k]
    assert secrets == []
    assert definition["logging"]["options"]["max-size"] == "${CHANNELFLOW_LOG_MAX_SIZE:-20m}"


@pytest.mark.trace("REQ-WP-099")
def test_the_hype_ingest_service_reads_the_hype_symbol_from_bybit() -> None:
    environment = services()["ingest-bybit-hype"]["environment"]

    assert environment["CHANNELFLOW_INGEST_VENUE"] == "bybit"
    assert environment["CHANNELFLOW_INGEST_SYMBOLS"].endswith(":-HYPEUSDT}")


@pytest.mark.trace("REQ-WP-099")
def test_the_okx_hype_ingest_reads_the_hype_swap_from_okx() -> None:
    environment = services()["ingest-okx-hype"]["environment"]

    assert environment["CHANNELFLOW_INGEST_VENUE"] == "okx"
    assert environment["CHANNELFLOW_INGEST_SYMBOLS"].endswith(":-HYPE-USDT-SWAP}")
