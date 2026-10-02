"""A venue's policy is defined once (REQ-WP-078).

# @trace: REQ-WP-078

`connectors/session.py` and `connectors/venue.py` each defined Binance's, Bybit's and
OKX's policy, with different numbers, and the live daemon read the second set -- the one
with the mistakes: Binance's 24-hour *stream lifetime* sitting in `idle_timeout_ns`,
OKX's ping interval 20 s against the 15 s that was measured to survive a hundred.
Nothing stopped the second definition appearing, so a deletion without this test is a
request for a third.

The collector imports every module of `channelflow.connectors` and groups every
`VenuePolicy` it finds by venue, so a definition added anywhere in the package is seen.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import channelflow.connectors as connectors_package
from channelflow.connectors.session import SECOND_NS, Keepalive, VenuePolicy

Found = dict[str, list[tuple[str, str, VenuePolicy]]]


def collect_policies() -> Found:
    found: Found = {}
    modules = [connectors_package.__name__]
    modules += [
        info.name
        for info in pkgutil.walk_packages(
            connectors_package.__path__, connectors_package.__name__ + "."
        )
    ]
    for module_name in modules:
        for attribute, value in vars(importlib.import_module(module_name)).items():
            if isinstance(value, VenuePolicy):
                found.setdefault(value.venue, []).append((module_name, attribute, value))
    return found


def disagreements(found: Found) -> list[str]:
    """One line per venue that has two policies which are not equal."""
    out = []
    for venue, definitions in sorted(found.items()):
        if len({policy for _, _, policy in definitions}) > 1:
            where = "; ".join(f"{module}.{name}" for module, name, _ in definitions)
            out.append(f"{venue} is defined with different values in: {where}")
    return out


@pytest.mark.trace("REQ-WP-078")
def test_each_venue_has_one_policy_across_the_connectors_package() -> None:
    assert disagreements(collect_policies()) == []


@pytest.mark.trace("REQ-WP-078")
def test_the_collector_sees_the_three_live_venues_and_hypercore() -> None:
    """If it found nothing it would find no disagreement, and pass."""
    assert set(collect_policies()) >= {"binance", "bybit", "okx", "hyperliquid"}


@pytest.mark.trace("REQ-WP-078")
def test_the_guard_can_fail() -> None:
    """A guard that has never seen the thing it forbids guards nothing."""

    def policy(idle: int) -> VenuePolicy:
        return VenuePolicy(
            venue="x",
            keepalive=Keepalive.CLIENT_INITIATED,
            idle_timeout_ns=idle * SECOND_NS,
            client_ping_interval_ns=SECOND_NS,
            ping_payload="ping",
        )

    differing = {"x": [("a", "ONE", policy(30)), ("b", "TWO", policy(31))]}
    same = {"x": [("a", "ONE", policy(30)), ("b", "TWO", policy(30))]}

    assert len(disagreements(differing)) == 1 and "a.ONE" in disagreements(differing)[0]
    assert disagreements(same) == []
