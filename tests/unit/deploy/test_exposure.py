"""What the stack publishes, and to whom (REQ-WP-072).

PRD §34's list is about the web API, but publishing a database to whatever can
reach the host is the larger version of the same mistake. Every service bound
its published port to **all interfaces** -- the bare `"${PORT}:…"` form -- under
a compose file whose Grafana block carried the comment *"this stack holds no
secrets and is not reachable from anywhere"*, a premise a deployment falsifies
while leaving the setting.

**Binding to loopback removes a question rather than answering it.** On Linux,
Docker inserts its rules into the `DOCKER` chain of the `nat` table, traversed
before the `INPUT` chain `ufw` manages by default -- so a published port can be
reachable while `ufw` reports it denied. A port that never listens on the
external interface cannot be reached however the firewall is configured.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"

BIND = "${CHANNELFLOW_BIND_ADDRESS:-127.0.0.1}"

#: Services deliberately reachable from outside the host, with the reason.
#: Empty: this deployment is reached through an SSH tunnel, so nothing needs to
#: listen on an external interface. Adding an entry is a decision, and it is
#: made here where somebody reviewing security will see it.
DELIBERATELY_PUBLIC: dict[str, str] = {}

_PORT_LINE = re.compile(r'^\s*-\s*"(?P<mapping>[^"]+)"\s*$')


def _published() -> dict[str, list[str]]:
    """Service -> the port mappings it publishes, read from the compose file."""
    mappings: dict[str, list[str]] = {}
    service: str | None = None
    in_ports = False
    for line in COMPOSE.read_text().splitlines():
        if re.match(r"^  [a-z0-9_-]+:\s*$", line):
            service = line.strip().rstrip(":")
            in_ports = False
            continue
        if re.match(r"^    ports:\s*$", line):
            in_ports = True
            continue
        if in_ports:
            found = _PORT_LINE.match(line)
            if found is None:
                in_ports = False
                continue
            assert service is not None
            mappings.setdefault(service, []).append(found.group("mapping"))
    return mappings


@pytest.mark.trace("REQ-WP-072")
def test_the_compose_file_still_publishes_ports() -> None:
    """Otherwise every assertion below passes over an empty set."""
    published = _published()
    assert len(published) >= 7, f"only found {sorted(published)}"
    assert "postgres" in published
    assert "grafana" in published


@pytest.mark.trace("REQ-WP-072")
def test_every_published_port_binds_an_address_we_chose() -> None:
    for service, mappings in sorted(_published().items()):
        if service in DELIBERATELY_PUBLIC:
            continue
        for mapping in mappings:
            assert mapping.startswith(f"{BIND}:"), (
                f"{service} publishes {mapping!r}, which binds all interfaces; "
                f"bind it through {BIND} or name it in DELIBERATELY_PUBLIC "
                "with a reason"
            )


@pytest.mark.trace("REQ-WP-072")
def test_a_public_service_has_to_give_a_reason() -> None:
    for service, reason in DELIBERATELY_PUBLIC.items():
        assert service in _published(), f"{service} is listed public but publishes nothing"
        assert len(reason) > 20, f"{service} is public for no stated reason"


@pytest.mark.trace("REQ-WP-072")
def test_the_bind_address_defaults_to_loopback() -> None:
    assert "CHANNELFLOW_BIND_ADDRESS=127.0.0.1" in ENV_EXAMPLE.read_text()


@pytest.mark.trace("REQ-WP-072")
def test_the_default_is_in_the_compose_file_not_only_in_the_template() -> None:
    """A security default has to fail closed, and .env.example is not a default.

    Measured: with the bare `${CHANNELFLOW_BIND_ADDRESS}` form, an `.env` written
    before the variable existed leaves it blank, and compose parses
    `":19092:9092"` as a published port with **no** host_ip -- every service on
    every interface, which is the opposite of what this file says it does. The
    inline `:-127.0.0.1` is what makes an unset variable safe rather than wide
    open.
    """
    text = COMPOSE.read_text()
    bare = re.findall(r'"\$\{CHANNELFLOW_BIND_ADDRESS\}:', text)
    assert bare == [], f"{len(bare)} port mappings would bind all interfaces if unset"
    assert text.count("${CHANNELFLOW_BIND_ADDRESS:-127.0.0.1}:") == 8


@pytest.mark.trace("REQ-WP-072")
def test_grafana_is_not_an_unconditional_anonymous_admin() -> None:
    text = COMPOSE.read_text()
    assert 'GF_AUTH_ANONYMOUS_ENABLED: "true"' not in text
    assert "GF_AUTH_ANONYMOUS_ORG_ROLE: Admin" not in text
    assert "GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?" in text, (
        "a bare substitution gives Grafana a blank password, and Grafana then "
        "falls back to `admin`; `:?` makes compose refuse and say so"
    )


@pytest.mark.trace("REQ-WP-072")
def test_grafanas_credentials_are_named_in_the_env_template() -> None:
    text = ENV_EXAMPLE.read_text()
    assert "GRAFANA_ADMIN_PASSWORD=" in text
    assert "GRAFANA_ANONYMOUS=" in text


@pytest.mark.trace("REQ-WP-072")
def test_the_compose_file_no_longer_says_ingest_binance_does_not_exist() -> None:
    """The comment sat directly above the service it said did not exist."""
    text = COMPOSE.read_text()
    assert "Neither exists as code" not in text
