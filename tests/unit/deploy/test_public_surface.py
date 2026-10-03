"""What the public address can reach (REQ-WP-080, FR-007).

Through a tunnel the only door is the web service's nginx. `/readyz`, `/metrics` and `/ws/market`
are
unreachable through it today, by the way two files line up: nginx proxies `/api/` only, and the API
serves those three at its root. Nothing checked that. These do, so the property survives the day
someone adds a `location /` that proxies everything.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from channelflow.api.app import create_app
from channelflow.api.repositories import InMemoryRepository
from channelflow.api.security import all_routes

ROOT = Path(__file__).resolve().parents[3]
NGINX = (ROOT / "apps" / "web" / "nginx.conf").read_text()


def _proxied_locations() -> list[str]:
    """Each `location` block that contains a `proxy_pass`."""
    found = []
    for match in re.finditer(r"location\s+(?:[=~*^]+\s+)?(\S+)\s*\{([^}]*)\}", NGINX):
        if "proxy_pass" in match.group(2):
            found.append(match.group(1))
    return found


@pytest.mark.trace("REQ-WP-080")
def test_nginx_proxies_exactly_one_location_and_it_is_api() -> None:
    assert _proxied_locations() == ["/api/"]


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("path", ["/readyz", "/metrics", "/ws/market"])
def test_the_routes_that_are_not_gated_are_outside_the_proxied_prefix(path: str) -> None:
    paths = {p for p, _ in all_routes(create_app(repository=InMemoryRepository()))}

    assert path in paths, f"{path} no longer exists; the premise of this test has changed"
    assert not any(path.startswith(prefix) for prefix in _proxied_locations())


@pytest.mark.trace("REQ-WP-080")
def test_everything_served_under_the_proxied_prefix_is_a_data_route() -> None:
    """If a route appears under `/api/` that is not `/api/v1/`, it is reachable through the tunnel
    and outside the gate's scope."""
    paths = {p for p, _ in all_routes(create_app(repository=InMemoryRepository()))}

    stray = sorted(p for p in paths if p.startswith("/api/") and not p.startswith("/api/v1/"))

    assert stray == []
