"""One stream lifecycle, three venues, and the differences written down.

# @trace: REQ-WP-051
# @trace: REQ-WP-078

PRD §0 item 10 requires new connectors to implement a shared canonical
interface, and §35.6 lists reconnect and rate limits among what connector tests
must cover. Until now only Binance had a session, and its rules were written
into its code as constants.

The transport and the clock are arguments, not imports -- [[REQ-WP-003]]'s shape,
and the reason the whole lifecycle is testable without opening a socket.

**Every venue difference here was measured, not read.** Three venues keep a
connection alive three different ways, and one of them tells you nothing when it
gives up:

    venue      idle close              keepalive
    ------------------------------------------------------------------
    Binance    -                       the venue pings, the client answers
    Bybit      ~60s, no close frame    the client sends `{"op":"ping"}`
    OKX        30s, code 4004          the client sends `ping`, bare text

Measured on 2026-09-12 by opening a connection, subscribing to nothing, and
timing the close. Three consequences that a documentation page would not have
made obvious:

* **Inbound data resets the timer on both venues.** Subscribed to a busy
  channel, neither closed in five and a half minutes without a client ping. The
  keepalive is for quiet subscriptions, not for every connection.
* **Bybit sends no close frame.** A client that waits for a clean close waits
  forever, so silence past the idle timeout is the only signal there is -- and
  this session treats it as a drop rather than as a quiet market.
* **OKX's ping is a bare string**, not JSON, and its pong is the bare string
  back. Bybit's is JSON both ways. The payload is part of the policy for that
  reason rather than being assembled from a venue name.

**The connect rate limit is the one fact here that is not measured.** Both
venues cap how often an address may open a connection, and establishing the cap
means exceeding it deliberately against a venue that has done nothing to deserve
it. The throttle is implemented and tested; the number in each policy is
conservative rather than discovered, and is marked as such.
"""

from __future__ import annotations

import logging
import queue
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

SECOND_NS = 1_000_000_000

logger = logging.getLogger(__name__)


class Keepalive(StrEnum):
    """Who is responsible for proving the connection is alive."""

    #: The venue pings and the client answers. Binance.
    SERVER_INITIATED = "server_initiated"
    #: The client pings and the venue answers. Bybit, OKX.
    CLIENT_INITIATED = "client_initiated"


class Transport(Protocol):
    """What a session needs from a connection. Deliberately four methods."""

    def connect(self, streams: tuple[str, ...]) -> None: ...
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...


class VenueConnector(Protocol):
    """Full connection lifecycle for one venue.

    Unlike `Transport`, this owns the full connection lifecycle including
    post-connect subscription (Bybit, OKX send a subscribe message after connect).
    """

    def connect(self, streams: tuple[str, ...]) -> None:
        """Open socket, send subscription if needed, start reader thread."""

    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    @property
    def frames(self) -> queue.Queue[str]: ...
    @property
    def alive(self) -> bool:
        """True from `connect` until the reader returns for **any** reason.

        A fact about the reader and not about the venue: a reader that is running but
        was never subscribed successfully is alive. The reader logs *why* it ended where
        the exception is in hand; the session only needs to know that it did.
        """
        ...


class Clock(Protocol):
    def now_ns(self) -> int: ...


class FakeClock:
    """A clock the tests drive, so the lifetime arithmetic is exercised by the
    same code path in tests and in production."""

    def __init__(self, start_ns: int = 0) -> None:
        self._now = start_ns

    def now_ns(self) -> int:
        return self._now

    def advance_ns(self, delta: int) -> None:
        self._now += delta


@dataclass(frozen=True)
class VenuePolicy:
    """What one venue expects of a client, in one place.

    Every field is here because a venue differs from its neighbours in it. A
    policy is data so the three can be read side by side; when they were code,
    the differences were three files apart.
    """

    venue: str
    keepalive: Keepalive

    #: How long the venue tolerates silence before closing. `None` where it was
    #: not measured. Measured by opening a connection and subscribing to
    #: nothing, which is the only state in which the timer is observable.
    idle_timeout_ns: int | None = None

    #: How often the client must send, comfortably inside the timeout.
    client_ping_interval_ns: int | None = None

    #: The payload, verbatim. OKX's is a bare string and Bybit's is JSON, which
    #: is why this is not assembled from the venue's name.
    ping_payload: str | None = None

    #: How long the venue keeps a connection before closing it regardless of
    #: traffic. Binance closes at 24 hours; nothing similar was observed on the
    #: other two, which is not the same as there being none.
    stream_lifetime_ns: int | None = None

    #: Whether the venue sends a close frame when it gives up. Bybit does not,
    #: so on that venue silence is the only signal there is.
    announces_close: bool = True

    #: The shortest gap between two connection attempts. Conservative rather
    #: than discovered: both venues cap this, and finding the cap means
    #: exceeding it against a venue that has done nothing to deserve it.
    min_connect_interval_ns: int = SECOND_NS

    #: How long **this system** tolerates a silent **venue** before reconnecting. Not
    #: `idle_timeout_ns`, which is how long the *venue* tolerates a silent *client* -- a
    #: different quantity that happens to be a duration too. Borrowing one for the other
    #: made Binance's silence threshold 48 hours (its 24-hour stream lifetime, doubled).
    max_silence_ns: int | None = None

    #: The longest the session waits between attempts while a venue keeps refusing: the
    #: delay doubles from `min_connect_interval_ns` and stops here.
    max_connect_backoff_ns: int = 60 * SECOND_NS

    def __post_init__(self) -> None:
        if self.keepalive is Keepalive.CLIENT_INITIATED:
            if self.ping_payload is None or self.client_ping_interval_ns is None:
                raise ValueError(
                    f"{self.venue}: a client-initiated keepalive needs a payload and an interval"
                )
            if self.idle_timeout_ns is not None and (
                self.client_ping_interval_ns >= self.idle_timeout_ns
            ):
                raise ValueError(
                    f"{self.venue}: pinging every {self.client_ping_interval_ns}ns cannot keep "
                    f"a connection the venue closes after {self.idle_timeout_ns}ns"
                )
        if self.max_silence_ns is not None:
            if self.max_silence_ns <= 0:
                raise ValueError(f"{self.venue}: max_silence_ns must be positive")
            if (
                self.client_ping_interval_ns is not None
                and self.max_silence_ns <= self.client_ping_interval_ns
            ):
                raise ValueError(
                    f"{self.venue}: max_silence_ns {self.max_silence_ns} is not longer than the "
                    f"ping interval {self.client_ping_interval_ns}; a healthy quiet connection "
                    "would be reconnected between two pongs"
                )
        if self.max_connect_backoff_ns < self.min_connect_interval_ns:
            raise ValueError(
                f"{self.venue}: the backoff ceiling {self.max_connect_backoff_ns} is below the "
                f"minimum connect interval {self.min_connect_interval_ns}"
            )


#: How long the three live venues may go without a frame before the session reconnects.
#:
#: **The basis, measured on 2026-10-02 from the raw archive.** The longest gap between two
#: consecutive frames was 22.2 s on Bybit BTCUSDT over 360 complete minutes (then 22.0 s
#: and 18.8 s), and 11.2 s within a minute on SOLUSDT over 309 sampled minutes. 60 s is
#: 2.7 and 5.4 times those. A 64.1 s gap also appeared, beginning 10:54:50; the container
#: started at 10:55:50, so it was this project's own restart and is not a basis for
#: anything. This is a starting point and not a derivation: a thinner symbol needs a longer
#: limit, which is what `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` is for.
LIVE_MAX_SILENCE_NS = 60 * SECOND_NS

#: Binance pings and expects a pong; its streams last a day. The 24 hours is a stream
#: *lifetime*: a connection is closed at that age however much traffic it carries. It
#: is not an idle timeout, and `venue.py` once put it in that field.
BINANCE = VenuePolicy(
    venue="binance",
    keepalive=Keepalive.SERVER_INITIATED,
    stream_lifetime_ns=24 * 60 * 60 * SECOND_NS,
    max_silence_ns=LIVE_MAX_SILENCE_NS,
)

#: Bybit closed an idle connection at 60.7 seconds with no close frame.
#: Pinging every twenty seconds survived a hundred, answered `{"ret_msg":"pong"}`.
BYBIT = VenuePolicy(
    venue="bybit",
    keepalive=Keepalive.CLIENT_INITIATED,
    idle_timeout_ns=60 * SECOND_NS,
    client_ping_interval_ns=20 * SECOND_NS,
    ping_payload='{"op":"ping"}',
    announces_close=False,
    max_silence_ns=LIVE_MAX_SILENCE_NS,
)

#: OKX closed an idle connection at 30.9 seconds with code 4004 and the message
#: "No data received in 30s." Pinging every fifteen seconds survived a hundred.
OKX = VenuePolicy(
    venue="okx",
    keepalive=Keepalive.CLIENT_INITIATED,
    idle_timeout_ns=30 * SECOND_NS,
    client_ping_interval_ns=15 * SECOND_NS,
    ping_payload="ping",
    max_silence_ns=LIVE_MAX_SILENCE_NS,
)

#: HyperCore closed an idle connection at 60.6 seconds with no close frame --
#: the same shape as Bybit, and the same consequence: silence is the only signal
#: there is. Pinging `{"method":"ping"}` every twenty seconds survived a
#: hundred, answered `{"channel":"pong"}`.
#:
#: A fourth venue and a fourth payload convention. Binance is pinged by the
#: venue; Bybit sends `{"op":"ping"}`; OKX sends the bare string `ping`; this one
#: sends `{"method":"ping"}`. Nothing about a venue's name predicts it.
HYPERCORE = VenuePolicy(
    venue="hyperliquid",
    keepalive=Keepalive.CLIENT_INITIATED,
    idle_timeout_ns=60 * SECOND_NS,
    client_ping_interval_ns=20 * SECOND_NS,
    ping_payload='{"method":"ping"}',
    announces_close=False,
)


def silence_limit_ns(policy: VenuePolicy) -> int | None:
    """How long a feed may be silent before the session reconnects, or `None` for never.

    The policy's own `max_silence_ns` if it has one. Otherwise, for a venue that gives up
    without saying so, its idle timeout -- what the session did before this field
    existed, and what HyperCore still relies on. A venue that announces its closes and
    names no limit has none.
    """
    if policy.max_silence_ns is not None:
        return policy.max_silence_ns
    if not policy.announces_close:
        return policy.idle_timeout_ns
    return None


POLICIES: dict[str, VenuePolicy] = {
    policy.venue: policy for policy in (BINANCE, BYBIT, OKX, HYPERCORE)
}


@dataclass
class ConnectorMetrics:
    """A connector that fails silently is indistinguishable from an idle one,
    and the difference matters at three in the morning."""

    connection_failures: int = 0
    sequence_gaps: int = 0
    normalization_failures: int = 0
    poll_failures: int = 0
    #: Reconnects the venue never announced -- inferred from silence.
    silent_drops: int = 0
    #: Reconnects deferred because the venue limits how often a client may
    #: connect. A connector that hammered a venue's limit would be throttled at
    #: the venue instead, which is worse and less visible.
    throttled_reconnects: int = 0
    #: Reconnects made because the connector's reader had ended (REQ-WP-078).
    dead_readers: int = 0


@dataclass
class StreamSession:
    """One websocket subscription and its lifecycle, driven by a venue policy."""

    streams: tuple[str, ...]
    policy: VenuePolicy
    connector: Any
    clock: Clock
    metrics: ConnectorMetrics = field(default_factory=ConnectorMetrics)

    _connected_at_ns: int = 0
    _last_inbound_ns: int = 0
    _last_ping_ns: int = 0
    _needs_snapshot: bool = True
    #: Reconnect bookkeeping (REQ-WP-078). Attempts since the feed last delivered a frame:
    #: recovery is a frame arriving, **not** `connect()` returning, because Bybit's and
    #: OKX's `connect()` only starts a thread and returns whether or not it will work.
    _attempts: int = 0
    _next_attempt_ns: int = 0
    _down_since_ns: int | None = None

    @property
    def needs_snapshot(self) -> bool:
        """True until a snapshot is taken, and true again after any reconnect."""
        return self._needs_snapshot

    def snapshot_taken(self) -> None:
        self._needs_snapshot = False

    def start(self) -> None:
        self._connect()

    def _connect(self) -> None:
        try:
            self.connector.connect(self.streams)
        except Exception:
            self.metrics.connection_failures += 1
            raise
        now = self.clock.now_ns()
        self._connected_at_ns = now
        self._last_inbound_ns = now
        self._last_ping_ns = now
        # Any new connection means the book must be rebuilt: updates that
        # arrived while disconnected cannot be recovered.
        self._needs_snapshot = True
        # The venue's connect limit: no second attempt inside it, whatever the reason.
        self._next_attempt_ns = now + self.policy.min_connect_interval_ns

    def _reconnect(self, kind: str, why: str) -> bool:
        """Close and open again, unless the venue's connect limit or the backoff says wait.

        Never raises. A `connect()` that fails -- Binance's raises `NotConnected` when the
        socket does not open -- is counted, logged and scheduled, because left to escape
        it would leave `tick` and end the daemon from inside a reconnect. (`start()` still
        raises: a daemon that cannot connect at all should fail loudly at start-up.)
        """
        now = self.clock.now_ns()
        routine = kind == "lifetime"
        if self._down_since_ns is None and not routine:
            self._down_since_ns = now
            logger.warning("%s connection down: %s", self.policy.venue, why)
        if now < self._next_attempt_ns:
            self.metrics.throttled_reconnects += 1
            return False

        self._attempts += 1
        attempts = self._attempts
        outcome = "connect() returned"
        try:
            self.connector.close()
            self._connect()
        except Exception as error:
            outcome = f"connect() failed: {error}"
        # Spaced min, 2*min, 4*min ... up to the ceiling, counted over attempts since the
        # feed last delivered, so a venue that accepts the socket and drops it is not
        # retried at the minimum interval for ever.
        delay = min(
            self.policy.min_connect_interval_ns * 2 ** (attempts - 1),
            self.policy.max_connect_backoff_ns,
        )
        self._next_attempt_ns = now + delay

        if routine:
            logger.info("%s reconnecting: %s", self.policy.venue, why)
        elif attempts >= 2 and attempts & (attempts - 1) == 0:
            # Logged at 2, 4, 8, 16...: the count of lines grows with the log of the
            # failures and not with their number.
            logger.warning(
                "%s still down after %d attempts (%s; %s)",
                self.policy.venue,
                attempts,
                why,
                outcome,
            )
        if kind == "silence":
            self.metrics.silent_drops += 1
        elif kind == "reader":
            self.metrics.dead_readers += 1
        return True

    def on_frame(self) -> None:
        """Anything arriving from the venue, including a pong.

        Both venues measured reset their idle timer on inbound data, so a pong
        counts: it is the venue answering, which is the only thing the timer is
        about.
        """
        now = self.clock.now_ns()
        self._last_inbound_ns = now
        if self._down_since_ns is not None:
            logger.info(
                "%s connection recovered after %d attempt(s), down for %.1f s",
                self.policy.venue,
                self._attempts,
                (now - self._down_since_ns) / SECOND_NS,
            )
            self._down_since_ns = None
        self._attempts = 0

    def on_ping(self) -> None:
        """The venue pinged us. Binance disconnects a client that does not answer."""
        self.connector.pong()
        self.on_frame()

    def tick(self) -> None:
        """Advance the lifecycle. Called on a timer by the ingestion loop; must not block.

        Reconnects, for **every** venue, on three grounds in this order: the stream has
        reached the age at which the venue closes it; the connector's reader has ended;
        nothing has arrived for longer than the venue is allowed to be silent.

        `announces_close` used to gate the last of these, on the belief that a venue which
        says when it gives up needs no second-guessing. Binance and OKX do say -- and
        nothing in the connectors turned what they said into a reconnect: the reader
        thread simply ended, and a Binance daemon whose socket died stayed `Up` for four
        days with no feed. The field now documents what was measured and decides nothing.
        """
        now = self.clock.now_ns()

        lifetime = self.policy.stream_lifetime_ns
        if lifetime is not None and now - self._connected_at_ns >= lifetime:
            self._reconnect("lifetime", f"the stream reached its {lifetime / SECOND_NS:.0f} s age")
            return

        if not self.connector.alive:
            self._reconnect("reader", "the connector's reader has ended")
            return

        limit = silence_limit_ns(self.policy)
        silent_for = now - self._last_inbound_ns
        if limit is not None and silent_for > limit:
            self._reconnect(
                "silence",
                f"silent for {silent_for / SECOND_NS:.0f} s (limit {limit / SECOND_NS:.0f} s)",
            )
            return

        interval = self.policy.client_ping_interval_ns
        if (
            self.policy.keepalive is Keepalive.CLIENT_INITIATED
            and interval is not None
            and now - self._last_ping_ns >= interval
        ):
            # Stamped first: a ping that fails is not retried on the next tick, which at the
            # daemon's step rate would be five warnings a second.
            self._last_ping_ns = now
            try:
                self.connector.send(self.policy.ping_payload or "")
            except Exception as error:  # noqa: BLE001 -- any failure to write is the same fact
                # The socket went between the reader's last look and this write. The
                # reader ending is what reconnects; a ping must not end the loop.
                logger.warning(
                    "%s: ping not sent: %s: %s", self.policy.venue, type(error).__name__, error
                )

    def record_sequence_gap(self) -> None:
        self.metrics.sequence_gaps += 1

    def record_normalization_failure(self) -> None:
        self.metrics.normalization_failures += 1

    def record_poll_failure(self) -> None:
        self.metrics.poll_failures += 1
