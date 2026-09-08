"""Getting the message out, and admitting when it did not go (PRD section 26.4).

# @trace: REQ-WP-008

Four requirements: retry with exponential backoff, a dead-letter record, a
delivery audit, and never block the signal engine on a Telegram failure.

ADR-018 turns the last one into a property. There is no HTTP client here and no
`sleep`: the transport arrives as an argument, and the backoff is *computed*
rather than waited out. Nothing in `deliver` can block, so "never blocks" is
not a promise about how carefully this was written.

`deliver` also never raises. A transport exception becomes an audit record --
an exception travelling back into the signal engine is exactly the blocking
this is meant to prevent, wearing a different shape.

The audit is append-only and is the observation point for every test here,
which is also what an operator reads when something has gone wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from channelflow.alerting.models import Alert, AttemptOutcome, AuditRecord
from channelflow.alerting.render import chart_deep_link, render_message

SECOND_NS = 1_000_000_000

#: The only response this treats as delivered. Anything else -- an error, or an
#: ambiguous success -- is retried: a delivery nobody can confirm is not one
#: (the spec's first edge case).
OK = "ok"


class Transport(Protocol):
    """Whatever actually sends the text.

    A protocol rather than a class, so this package holds no HTTP client and no
    credential. The real Telegram adapter belongs behind the connector
    boundary; the tests pass a ten-line fake.
    """

    def send(self, text: str, *, link: str) -> str: ...


@dataclass
class Dispatcher:
    """Delivery, retry, dead-lettering and the audit of all three."""

    transport: Transport
    max_attempts: int = 3
    backoff_base_ns: int = SECOND_NS
    audit: list[AuditRecord] = field(default_factory=list)
    dead_letters: list[Alert] = field(default_factory=list)

    def deliver(self, alert: Alert, *, at_ns: int) -> AuditRecord:
        """Try to send, up to the attempt budget. Never raises.

        `at_ns` is an event time, and the attempt timestamps are derived from
        it by the computed backoff -- so replaying a stream produces an
        identical audit (ADR-018, Principle VII).
        """
        text = render_message(alert)
        link = chart_deep_link(alert)

        attempts: list[AttemptOutcome] = []
        for attempt in range(1, self.max_attempts + 1):
            attempt_at = at_ns + sum(self.backoff_ns(i) for i in range(1, attempt))
            ok, detail = self._try(text, link)
            attempts.append(AttemptOutcome(attempt=attempt, ok=ok, detail=detail, at_ns=attempt_at))
            if ok:
                return self._record(alert, at_ns, "delivered", "delivered", attempts)

        self.dead_letters.append(alert)
        return self._record(
            alert,
            at_ns,
            "dead_lettered",
            f"no delivery after {self.max_attempts} attempt(s): {attempts[-1].detail}",
            attempts,
        )

    def suppress(self, alert: Alert, *, at_ns: int, reason: str) -> AuditRecord:
        """Record an alert that was deliberately not sent.

        A suppression that left no trace would be indistinguishable from there
        having been no setup, which is the spec's third US5 scenario.
        """
        return self._record(alert, at_ns, "suppressed", reason, ())

    def backoff_ns(self, attempt: int) -> int:
        """Delay before `attempt`. Computed; the waiting is the caller's."""
        return int(self.backoff_base_ns * 2 ** (attempt - 1))

    def _try(self, text: str, link: str) -> tuple[bool, str]:
        try:
            response = self.transport.send(text, link=link)
        except Exception as exc:  # noqa: BLE001 -- the whole point is that
            # nothing escapes into the signal engine (PRD section 26.4).
            return False, f"{type(exc).__name__}: {exc}"
        if response == OK:
            return True, OK
        return False, f"unexpected response: {response!r}"

    def _record(
        self,
        alert: Alert,
        at_ns: int,
        status: str,
        reason: str,
        attempts: tuple[AttemptOutcome, ...] | list[AttemptOutcome],
    ) -> AuditRecord:
        record = AuditRecord(
            signal_id=alert.signal_id,
            symbol=alert.candidate.symbol,
            queued_at_ns=at_ns,
            status=status,  # type: ignore[arg-type]
            reason=reason,
            attempts=tuple(attempts),
        )
        self.audit.append(record)
        return record
