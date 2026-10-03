"""The Telegram profile: a tunnel in front of the web service, and nothing else (REQ-WP-080).

# @trace: REQ-WP-080

Telegram opens a Mini App only over HTTPS. `lexa-reader` reaches it through a Cloudflare Tunnel: an
outbound connection from the box to Cloudflare, which serves the public hostname and terminates TLS,
so no port is opened and no certificate lives on the host. The same shape here, as an **optional**
profile: without `--profile telegram` nothing new runs.

Read as YAML, as data, so a change to the file fails here on the commit that makes it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]
ENV_EXAMPLE = (ROOT / ".env.example").read_text()
DOC = (ROOT / "docs" / "deployment.md").read_text()

NEW_VARIABLES = (
    "CHANNELFLOW_TELEGRAM_AUTH",
    "CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS",
    "CHANNELFLOW_TUNNEL_TOKEN",
    "CHANNELFLOW_TUNNEL_PROTOCOL",
)


@pytest.mark.trace("REQ-WP-080")
def test_the_tunnel_exists_and_belongs_to_the_telegram_profile() -> None:
    assert COMPOSE["cloudflared"]["profiles"] == ["telegram"]


@pytest.mark.trace("REQ-WP-080")
def test_nothing_else_is_in_the_profile() -> None:
    """Whoever enables the profile gets a tunnel, not a different stack."""
    in_profile = sorted(
        name for name, definition in COMPOSE.items() if "telegram" in definition.get("profiles", [])
    )

    assert in_profile == ["cloudflared"]


@pytest.mark.trace("REQ-WP-080")
def test_the_tunnel_publishes_no_port() -> None:
    assert "ports" not in COMPOSE["cloudflared"]


@pytest.mark.trace("REQ-WP-080")
def test_the_tunnel_waits_for_the_web_service() -> None:
    depends = COMPOSE["cloudflared"]["depends_on"]
    names = list(depends) if isinstance(depends, dict) else depends

    assert names == ["web"]


@pytest.mark.trace("REQ-WP-080")
def test_the_image_is_pinned_to_a_version_and_not_latest() -> None:
    image = COMPOSE["cloudflared"]["image"]

    assert image.startswith("cloudflare/cloudflared:")
    assert image.split(":", 1)[1] not in {"latest", ""}


@pytest.mark.trace("REQ-WP-080")
def test_the_token_has_an_empty_default_and_is_not_required() -> None:
    """`${VAR:?}` is evaluated for every service, active profile or not, and would make
    `docker compose config` fail for everyone who never turns the profile on. An empty token makes
    cloudflared fail visibly at start instead."""
    env = COMPOSE["cloudflared"]["environment"]

    assert env["TUNNEL_TOKEN"] == "${CHANNELFLOW_TUNNEL_TOKEN:-}"
    assert ":?" not in str(env)


@pytest.mark.trace("REQ-WP-080")
def test_the_transport_defaults_to_http2_because_this_host_blocks_quic() -> None:
    """Found by `lexa-reader` on this very host: UDP egress to Cloudflare's edge is blocked, and the
    default (QUIC) never connects."""
    env = COMPOSE["cloudflared"]["environment"]

    assert env["TUNNEL_TRANSPORT_PROTOCOL"] == "${CHANNELFLOW_TUNNEL_PROTOCOL:-http2}"


@pytest.mark.trace("REQ-WP-080")
def test_the_api_is_told_the_mode_the_age_and_the_token() -> None:
    """Compose forwards only the variables a service names."""
    env = COMPOSE["api"]["environment"]

    assert env["CHANNELFLOW_TELEGRAM_AUTH"] == "${CHANNELFLOW_TELEGRAM_AUTH:-off}"
    assert "CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS" in env
    assert env["TELEGRAM_BOT_TOKEN"] == "${TELEGRAM_BOT_TOKEN:-}"


@pytest.mark.trace("REQ-WP-080")
def test_only_the_api_is_given_the_bot_token() -> None:
    """A secret goes to the one process that needs it."""
    holders = sorted(
        name
        for name, definition in COMPOSE.items()
        if "TELEGRAM_BOT_TOKEN" in str(definition.get("environment", {}))
    )

    assert holders == ["api"]


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("name", NEW_VARIABLES)
def test_every_new_variable_is_in_the_example_and_the_document(name: str) -> None:
    assert re.search(rf"^{name}=", ENV_EXAMPLE, re.M), f"{name} is not in .env.example"
    assert f"`{name}`" in DOC, f"{name} is not in docs/deployment.md"


@pytest.mark.trace("REQ-WP-080")
def test_the_example_carries_no_token_for_the_tunnel_or_the_bot() -> None:
    for name in ("CHANNELFLOW_TUNNEL_TOKEN", "TELEGRAM_BOT_TOKEN"):
        line = re.search(rf"^{name}=(.*)$", ENV_EXAMPLE, re.M)
        assert line is not None and line.group(1).strip() == "", name


@pytest.mark.trace("REQ-WP-080")
def test_the_document_says_how_to_start_it_and_what_the_gate_is() -> None:
    assert "--profile telegram" in DOC
    assert "BotFather" in DOC
    assert "access control" in DOC.lower(), "the document must say the gate is not secrecy"
