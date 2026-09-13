"""The data directory the stack writes into (REQ-WP-065).

The compose file and `tools/deploy/data_dir.py` are the two halves of one
decision: which services keep state, where, and as whom. Neither can check
itself, so this checks them against each other -- the same reasoning
`test_pane_features.py` applies to the pane list and the feature registry.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.deploy.data_dir import SERVICES

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = (ROOT / "docker-compose.yml").read_text()

#: `${CHANNELFLOW_DATA_DIR:-./data}/<directory>:<mount>`
_MOUNT = re.compile(r"\$\{CHANNELFLOW_DATA_DIR:-\./data\}/([\w-]+):([\w/.-]+)")


class ComposeUnreadable(AssertionError):
    """The compose file no longer declares mounts the way this test reads them."""


def bind_mounts() -> dict[str, str]:
    found = dict(_MOUNT.findall(COMPOSE))
    if not found:
        raise ComposeUnreadable(
            "no data-directory bind mounts found; the compose file changed shape and "
            "every assertion below would pass over an empty mapping"
        )
    return found


@pytest.mark.trace("REQ-WP-065")
def test_the_parser_fails_rather_than_finding_nothing() -> None:
    """The guard that keeps this file honest. A parser that returned an empty
    mapping would make every check below pass while checking nothing."""
    global COMPOSE  # noqa: PLW0603
    original = COMPOSE
    try:
        COMPOSE = "services:\n  postgres:\n    volumes:\n      - postgres_data:/data\n"
        with pytest.raises(ComposeUnreadable, match="changed shape"):
            bind_mounts()
    finally:
        COMPOSE = original


@pytest.mark.trace("REQ-WP-065")
def test_every_stateful_service_writes_into_the_data_directory() -> None:
    assert set(bind_mounts()) == {service.directory for service in SERVICES}


@pytest.mark.trace("REQ-WP-065")
def test_the_mount_points_agree_with_the_compose_file() -> None:
    """A directory prepared for the wrong mount point is prepared for nothing."""
    mounts = bind_mounts()
    for service in SERVICES:
        assert mounts[service.directory] == service.mount


@pytest.mark.trace("REQ-WP-065")
def test_no_named_volume_remains() -> None:
    """A leftover named volume is a service whose data is still inside Docker,
    and it would look identical from outside until the disk was moved."""
    assert not re.search(r"^volumes:$", COMPOSE, re.M)
    assert "_data:" not in COMPOSE


@pytest.mark.trace("REQ-WP-065")
def test_the_users_are_the_ones_the_images_run_as() -> None:
    """Read from the pinned images, not from documentation. Written out here so
    a changed image tag that moves a uid fails this rather than the server."""
    by_name = {service.name: service for service in SERVICES}

    assert (by_name["postgres"].uid, by_name["minio"].uid) == (0, 0)
    assert by_name["redpanda"].uid == 101
    assert by_name["prometheus"].uid == 65534
    assert by_name["grafana"].uid == 472


@pytest.mark.trace("REQ-WP-065")
def test_the_data_directory_is_never_committed_or_built_into_an_image() -> None:
    assert "/data/" in (ROOT / ".gitignore").read_text()
    assert re.search(r"^data$", (ROOT / ".dockerignore").read_text(), re.M)


@pytest.mark.trace("REQ-WP-065")
def test_the_directory_is_a_variable_so_a_server_needs_no_edit() -> None:
    assert "CHANNELFLOW_DATA_DIR" in (ROOT / ".env.example").read_text()
    # A default, so a fresh checkout works without one being set.
    assert "${CHANNELFLOW_DATA_DIR:-./data}" in COMPOSE
