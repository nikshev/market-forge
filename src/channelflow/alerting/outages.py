"""PRD section 45's Phase 8 line: alerting on data outages.

# @trace: REQ-WP-035

Three things this has to get right, and each failure produces a system that
looks monitored.

**Announce transitions, not states.** A feed hovering at a threshold alerts on
every observation, and a channel that cries constantly is one nobody reads --
losing the outage exactly as silence would, but expensively.

**Announce the recovery.** Silence after a failure notice reads as "still down"
and as "nobody is watching" equally well, and the reader cannot tell which. The
all-clear is also the half a system reliably forgets, because a recovery feels
like the absence of a problem rather than an event.

**Do not look like a trading signal.** Both travel the same wire to the same
reader, who acts on one and investigates the other, and a reader who confuses
them at a glance does the wrong thing quickly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from urllib.parse import quote

from channelflow.alerting.dispatch import Dispatcher
from channelflow.alerting.models import AuditRecord
from channelflow.health import FeedHealth, HealthState

#: Fixed, so the digest is stable across processes and releases ([[ADR-017]]).
OUTAGE_NAMESPACE = uuid.UUID("8d21f6ac-4b70-5e39-a1c8-63b5d907fe42")

SECOND_NS = 1_000_000_000


@dataclass(frozen=True)
class OutageAlert:
    """One change in what a feed is worth.

    `previous` is what it was before, and `bad_for_ns` is how long it had been
    bad when it recovered -- `None` when it has not.
    """

    health: FeedHealth
    previous: HealthState | None
    chart_base_url: str
    bad_for_ns: int | None = None

    @property
    def notification_id(self) -> uuid.UUID:
        key = f"{self.health.feed}|{self.health.observed_at_ns}|{self.health.state.name}"
        return uuid.uuid5(OUTAGE_NAMESPACE, key)

    @property
    def symbol(self) -> str:
        return self.health.feed

    @property
    def recovered(self) -> bool:
        return self.health.state is HealthState.GOOD

    def render(self) -> str:
        return render_outage(self)

    def link(self) -> str:
        return (
            f"{self.chart_base_url.rstrip('/')}"
            f"/health/{quote(self.health.feed)}"
            f"?at={self.health.observed_at_ns}"
        )


def render_outage(alert: OutageAlert) -> str:
    """The message, as an operator sees it.

    The header carries the word DATA and neither of the other two notifications'
    words, so a reader scanning a phone knows in one glance whether this is
    something to act on or something to investigate.
    """
    health = alert.health
    was = "unwatched" if alert.previous is None else alert.previous.name

    if alert.recovered:
        lines = [
            f"✅ {health.feed} — DATA RECOVERED",
            "",
            f"Was:            {was}",
            f"Now:            {health.state.name}",
        ]
        # Always present on a recovery, and zero is a duration: a feed bad and
        # good within one instant was bad for no time, which is a fact and not
        # an absence.
        if alert.bad_for_ns is not None:
            lines.append(f"Bad for:        {alert.bad_for_ns / SECOND_NS:.0f}s")
    else:
        lines = [
            f"⚠️ {health.feed} — DATA {health.state.name}",
            "",
            f"Was:            {was}",
            f"Now:            {health.state.name}",
        ]

    lines += ["", "Why:", health.reason]
    return "\n".join(lines)


@dataclass
class OutageWatch:
    """What each feed was last seen to be worth, and what is worth saying.

    Holds one entry per feed. A feed first seen bad is announced -- waiting for
    a prior good state would stay silent through an outage that began before
    this process did -- and a feed first seen good is not, because announcing a
    recovery from nothing reports an outage that never happened.
    """

    dispatcher: Dispatcher
    chart_base_url: str
    _last: dict[str, HealthState] = field(default_factory=dict)
    _bad_since: dict[str, int] = field(default_factory=dict)

    def observe(self, health: FeedHealth) -> AuditRecord | None:
        """Announce a change, or say nothing at all."""
        previous = self._last.get(health.feed)
        self._last[health.feed] = health.state

        if previous == health.state:
            return None

        good = health.state is HealthState.GOOD
        if good and previous is None:
            # First sight, and nothing wrong. There is no outage to close.
            return None

        bad_for: int | None = None
        if good:
            since = self._bad_since.pop(health.feed, None)
            bad_for = None if since is None else health.observed_at_ns - since
        elif previous is None or previous is HealthState.GOOD:
            self._bad_since[health.feed] = health.observed_at_ns

        alert = OutageAlert(
            health=health,
            previous=previous,
            chart_base_url=self.chart_base_url,
            bad_for_ns=bad_for,
        )
        return self.dispatcher.deliver(alert, at_ns=health.observed_at_ns)
