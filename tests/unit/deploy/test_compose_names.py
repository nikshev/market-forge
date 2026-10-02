"""Services reach each other by name, never by a container's address (REQ-WP-076).

# @trace: REQ-WP-076

Commit 8192826 replaced every `postgres` and `minio` in the compose file with
`172.24.0.8` and `172.24.0.12` -- nine services' worth -- as a way round a DNS
failure. It worked on the day, because those were the addresses Docker had
handed out. Recreating the two containers swapped them: `postgres` came back as
`.12` and `minio` as `.8`, so every service holding the old values would have
sent database traffic to the object store and the other way round, with no
error that named the cause.

An address is assigned at start-up and means nothing after the container is
recreated, a host reboots, or the stack is brought up from a fresh clone, which
is what `docs/deployment.md` tells a reader to do. A name is the thing the
compose network is for.

The test reads the file rather than asking Docker, so it fails in the fast gate,
on the commit that introduces the address, and not on whichever host first
recreates a container.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"

#: Four dotted decimals, minus the two that are not an address anybody assigned.
#: Loopback is the container itself -- every healthcheck here asks it a question
#: -- and `${CHANNELFLOW_BIND_ADDRESS:-127.0.0.1}` is REQ-WP-072's fail-closed
#: default. `0.0.0.0` is "every interface", a statement about a bind rather than
#: a destination. Everything else is somebody's address, and in a compose file
#: the only addresses that appear are the ones Docker handed out.
_ADDRESS = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w.])")
_NOT_ASSIGNED = re.compile(r"^(127\.|0\.0\.0\.0$)")


def _addresses(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        code = line.split("#", 1)[0]
        found.extend(
            (number, match.group())
            for match in _ADDRESS.finditer(code)
            if not _NOT_ASSIGNED.match(match.group())
        )
    return found


@pytest.mark.trace("REQ-WP-076")
def test_the_compose_file_names_no_container_by_address() -> None:
    """Nothing in the file is an IPv4 literal outside a comment."""
    found = _addresses(COMPOSE.read_text())
    assert not found, (
        "the compose file reaches a service by address, which is assigned at "
        f"start-up and changes when the container is recreated: {found}"
    )


@pytest.mark.trace("REQ-WP-076")
def test_the_check_sees_the_address_it_exists_to_catch() -> None:
    """A guard that has never seen the thing it forbids guards nothing.

    This is the line commit 8192826 wrote, so the pattern is shown to match what
    actually went wrong rather than what it was imagined to look like.
    """
    wrong = (
        "      CHANNELFLOW_CATALOG_URI: "
        "postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@172.24.0.8:5432/${POSTGRES_DB}\n"
        "      CHANNELFLOW_S3_ENDPOINT: http://172.24.0.12:9000\n"
    )
    assert [address for _, address in _addresses(wrong)] == ["172.24.0.8", "172.24.0.12"]


@pytest.mark.trace("REQ-WP-076")
def test_a_comment_mentioning_an_address_is_not_a_finding() -> None:
    assert _addresses("      # was 172.24.0.8 before the fix\n") == []


@pytest.mark.trace("REQ-WP-076")
def test_loopback_and_the_any_address_are_not_findings() -> None:
    """The two literals this file legitimately contains today."""
    assert _addresses('      - "${CHANNELFLOW_BIND_ADDRESS:-127.0.0.1}:${API_PORT}:8000"\n') == []
    assert _addresses("      test: curl http://127.0.0.1:8000/readyz\n") == []
    assert _addresses("      listen 0.0.0.0\n") == []
