"""A poll returns as soon as anything has arrived (REQ-WP-108).

`confluent_kafka`'s `consume(num_messages, timeout)` waits until it has `num_messages` or the
timeout runs out, whichever comes first. The poll passed its whole remaining wait as that timeout
and `limit` (500) as the count, so a trickle of messages was held for the full second before it
was returned: the live chart's price moved once a second, in bursts, and the owner -- comparing it
with Investing -- said it did not move. The docstring already promised what this pins: "once
anything has arrived this returns it".
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from channelflow.transport.kafka import _Consumer

pytestmark = pytest.mark.trace("REQ-WP-108")


@dataclass
class Message:
    def error(self) -> None:
        return None

    def topic(self) -> str:
        return "market.bar_forming.v1"

    def key(self) -> bytes:
        return b"bybit:BTCUSDT"

    def value(self) -> bytes:
        return b'{"x": 1}'

    def headers(self) -> list[tuple[str, bytes]]:
        return [
            ("event_time_ns", b"1"),
            ("ingest_time_ns", b"2"),
            ("producer", b"p"),
        ]


@dataclass
class Client:
    """Returns nothing for `empty` calls, then one message; remembers what it was asked for."""

    empty: int = 0
    timeouts: list[float] = field(default_factory=list)

    def consume(self, num_messages: int, timeout: float) -> list[Any]:
        self.timeouts.append(timeout)
        # A real client blocks for the timeout when it has fewer messages than it was asked for.
        time.sleep(min(timeout, 0.2) if self.empty > 0 else 0)
        if self.empty > 0:
            self.empty -= 1
            return []
        return [Message()]


def test_no_single_wait_is_longer_than_a_tenth_of_a_second() -> None:
    client = Client(empty=2)

    _Consumer(client).poll(limit=500, timeout=8.0)

    assert max(client.timeouts) <= 0.1, client.timeouts


def test_a_message_that_arrives_is_returned_without_waiting_for_the_deadline() -> None:
    client = Client(empty=1)

    started = time.monotonic()
    got = _Consumer(client).poll(limit=500, timeout=8.0)
    elapsed = time.monotonic() - started

    assert len(got) == 1
    assert elapsed < 1.0


def test_an_empty_topic_still_waits_out_the_timeout_and_answers_empty() -> None:
    client = Client(empty=10_000)

    started = time.monotonic()
    got = _Consumer(client).poll(limit=500, timeout=0.3)
    elapsed = time.monotonic() - started

    assert got == []
    assert 0.25 <= elapsed < 1.0
