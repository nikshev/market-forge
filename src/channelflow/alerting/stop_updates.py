"""PRD section 44A.34's stop-update notification.

# @trace: REQ-WP-034

Every line of the section's message is a **transition**:

    Entry:          112,400
    Old stop:       111,180
    New stop:       112,060
    Price:          113,740

    Position phase: STRUCTURE_TRAIL
    Open risk:      1.00R -> 0.28R

A notification saying only where the stop now sits reports what the chart
already shows and withholds the one thing it does not -- how much risk just came
off. A renderer that lost the "from" half of each pair would still produce a
message that looks complete.

`stop_in_force` is the second thing this module exists for. [[REQ-WP-033]]
separated the stop the policy has *decided* from the one the exchange is
*obeying*, so "old stop" now has two possible referents, and one of them
announces a move from a level that was never in force -- a change that did not
happen, in a message whose only job is to say what changed. It is carried rather
than derived: deriving it would mean this notification re-deciding what was
active, and that is the replay's answer to give.

Section 44A.34 ends with a rate limit -- "Do not notify for rejected
micro-updates unless debug mode is enabled" -- and `StopUpdateGate` is it. Stop
policies hold far more often than they move, and a channel reporting every held
micro-adjustment trains its reader to ignore it, at which point the alerts that
matter are lost exactly as silence would have lost them, but expensively.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from channelflow.alerting.dispatch import Dispatcher
from channelflow.alerting.models import AuditRecord
from channelflow.stops import PositionState, StopProposal

#: A fixed namespace, so the digest is stable across processes and releases
#: ([[ADR-017]]). Regenerating it would change every notification id in
#: existence.
STOP_NAMESPACE = uuid.UUID("2c9f5b71-0a3d-5e84-b6c2-7f1904ad8e35")


class StopUpdateAlert(BaseModel):
    """One stop decision, and everything needed to announce it.

    Frozen, for the reason `Alert` is: PRD section 0.5 forbids rewriting a
    finalized record, and this describes what was true when it was queued.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    position: PositionState
    proposal: StopProposal
    #: What the exchange was obeying when the decision was made -- not the last
    #: level the policy decided. See the module docstring.
    stop_in_force: Decimal = Field(gt=0)
    market_price: Decimal = Field(gt=0)
    event_time_ns: int = Field(ge=0)
    #: No default. A hard-coded host works in exactly one deployment.
    chart_base_url: str = Field(min_length=1)

    @property
    def notification_id(self) -> uuid.UUID:
        """Derived from the position and the decision instant ([[ADR-017]]).

        A generated id would make a replay produce different notifications,
        different dedupe decisions and a different audit, every one of them
        looking correct.
        """
        key = f"{self.position.position_id}|{self.proposal.at_ns}|{self.proposal.price}"
        return uuid.uuid5(STOP_NAMESPACE, key)

    @property
    def symbol(self) -> str:
        return self.position.instrument_id

    @property
    def open_risk_before_r(self) -> float:
        return self._risk(self.stop_in_force)

    @property
    def open_risk_after_r(self) -> float:
        """Floors at zero: a stop past entry leaves no open risk, and zero there
        is a reading rather than an absence."""
        return self._risk(self.proposal.price)

    def _risk(self, stop: Decimal) -> float:
        entry = self.position.average_entry_price
        gap = entry - stop if self.position.side == "LONG" else stop - entry
        return max(0.0, float(gap / self.position.initial_risk_per_unit))

    def render(self) -> str:
        return render_stop_update(self)

    def link(self) -> str:
        return position_deep_link(self)


def render_stop_update(alert: StopUpdateAlert) -> str:
    """Section 44A.34's message, as a reader sees it."""
    position = alert.position
    moved = alert.proposal.moved
    # "STOP UPDATED" above a stop that did not move is a false sentence, and
    # debug mode is the one place a reader is looking precisely because they do
    # not trust what is happening.
    headline = "STOP UPDATED" if moved else "STOP HELD"

    lines = [
        f"🛡 {alert.symbol} {position.side} — {headline}",
        "",
        f"Entry:          {_thousands(position.average_entry_price)}",
        f"Old stop:       {_thousands(alert.stop_in_force)}",
        f"New stop:       {_thousands(alert.proposal.price)}",
        f"Price:          {_thousands(alert.market_price)}",
        "",
        f"Position phase: {alert.proposal.phase.value}",
        f"Open risk:      {alert.open_risk_before_r:.2f}R -> {alert.open_risk_after_r:.2f}R",
    ]

    # Absent, never dashed ([[ADR-016]]): a dash where a value sits in every
    # other message is a formatting difference, not an absence, and a reader
    # scanning on a phone reads the shape before the numbers.
    if alert.proposal.anchor is not None:
        lines += ["", "Anchor:", alert.proposal.anchor.description]

    # Verbatim, including a code this build has never heard of. A dropped reason
    # is a newly added veto that reads as no veto at all.
    lines += ["", "Reasons:"]
    lines += [f"+ {reason.value}" for reason in alert.proposal.reasons]

    lines += ["", "[ OPEN POSITION CHART ]"]
    return "\n".join(lines)


def position_deep_link(alert: StopUpdateAlert) -> str:
    """Section 44A.34's button. The host is the alert's own, never a constant."""
    venue = alert.position.venue or "unknown"
    return (
        f"{alert.chart_base_url.rstrip('/')}"
        f"/position/{quote(venue)}/{quote(alert.symbol)}"
        f"?position={alert.position.position_id}"
        f"&at={alert.event_time_ns}"
    )


@dataclass
class StopUpdateGate:
    """Section 44A.34's rate limit: announce a move, and little else.

    `debug` widens what is announced. It does not invent events, and it does not
    render a hold in an update's shape.
    """

    dispatcher: Dispatcher
    debug: bool = False

    def offer(self, alert: StopUpdateAlert, *, at_ns: int) -> AuditRecord:
        if not alert.proposal.moved and not self.debug:
            reasons = ", ".join(reason.name for reason in alert.proposal.reasons)
            return self.dispatcher.suppress(
                alert,
                at_ns=at_ns,
                reason=f"the stop did not move ({reasons}); debug mode is off",
            )
        return self.dispatcher.deliver(alert, at_ns=at_ns)


def _thousands(value: Decimal) -> str:
    """Section 44A.34's `112,400`. Whole units: a stop quoted to eight decimals
    in a phone notification is a number nobody reads."""
    return f"{value:,.0f}"
