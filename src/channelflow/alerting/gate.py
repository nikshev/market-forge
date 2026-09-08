"""The last check before anything is said (PRD section 25.6).

# @trace: REQ-WP-008

Section 25.6 lists six alert-quality metrics -- precision, recall, false alert
rate, frequency, duplicate rate, and "stale-data alert count". Only the last
carries a required value: **must be zero**. It is the one number in the whole
document specified as an absolute, so it is enforced rather than measured.

The reasoning is not subtle. A setup computed from a book that stopped updating
describes a market that may have moved since. Sending it anyway is worse than
silence, because a reader cannot tell a stale alert from a fresh one -- they
look identical, and the stale one is more likely to be acted on, being the
first to arrive after a quiet spell.

A suppression is recorded, never silent: an alert that vanishes is
indistinguishable from there having been no setup, and the difference matters
to whoever is asking why they heard nothing all morning.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.alerting.dispatch import Dispatcher
from channelflow.alerting.models import Alert, AuditRecord
from channelflow.book import BookHealth

#: What counts as stale depends on the timeframe being traded, so it is an
#: argument -- Principle X, and PRD section 13.11's warning about defaults.
DEFAULT_STALENESS_TOLERANCE_NS = 5 * 1_000_000_000


@dataclass
class AlertGate:
    """Freshness first, then delivery."""

    dispatcher: Dispatcher
    staleness_tolerance_ns: int = DEFAULT_STALENESS_TOLERANCE_NS

    def offer(self, alert: Alert, *, health: BookHealth, at_ns: int) -> AuditRecord:
        """Deliver the alert, or record why it was not delivered."""
        if not health.valid:
            return self.dispatcher.suppress(
                alert,
                at_ns=at_ns,
                reason=(
                    f"book is invalid after {health.gap_count} sequence gap(s); "
                    "PRD section 11.1 rule 6 forbids emitting from it"
                ),
            )
        if health.stale_ns > self.staleness_tolerance_ns:
            return self.dispatcher.suppress(
                alert,
                at_ns=at_ns,
                reason=(
                    f"book is stale by {health.stale_ns}ns, over the "
                    f"{self.staleness_tolerance_ns}ns tolerance; PRD section 25.6 "
                    "requires the stale-data alert count to be zero"
                ),
            )
        return self.dispatcher.deliver(alert, at_ns=at_ns)
