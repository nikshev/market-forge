"""Whether this has already been said (PRD section 26.2).

# @trace: REQ-WP-008

Section 26.2 permits a repeat only when the score improves by a delta, the
signal changes phase, or the cooldown elapsed *and* a new independent touch
occurred. The score clause is not implemented: ADR-016 leaves the score to PRD
section 43's ranker, and there is nothing here to improve by a delta.

The third clause has two halves, and the second is easy to drop. A cooldown
that alone re-armed the alerter would repeat an unchanged confirmed setup every
half hour for as long as it stayed confirmed -- which, per ADR-010, is
indefinitely, because nothing yet resolves a confirmation.

Keyed on the derived signal id (ADR-017), so "the same setup" is a tuple
comparison rather than a similarity judgement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from channelflow.alerting.models import signal_id_for
from channelflow.signals import Candidate, CandidateState

#: PRD section 13.11's warning applies: a research default, not a proven
#: parameter, which is why it is an argument.
DEFAULT_COOLDOWN_NS = 30 * 60 * 1_000_000_000


@dataclass(frozen=True)
class _Said:
    signal_id: uuid.UUID
    state: CandidateState
    at_ns: int


@dataclass
class DedupePolicy:
    """What has already been said about each setup."""

    cooldown_ns: int = DEFAULT_COOLDOWN_NS
    #: Keyed by venue+symbol+timeframe: the cooldown is about how often a
    #: reader hears from one market, not about one candidate.
    _last: dict[tuple[str, str, int], _Said] = field(default_factory=dict)

    def should_send(self, candidate: Candidate, *, at_ns: int) -> bool:
        """Decide, and record the decision when it is yes.

        `at_ns` is an event time. Nothing here reads a clock (ADR-018).
        """
        market = (candidate.venue, candidate.symbol, candidate.timeframe_ns)
        signal_id = signal_id_for(candidate)
        previous = self._last.get(market)

        if previous is None:
            self._last[market] = _Said(signal_id, candidate.state, at_ns)
            return True

        same_setup = previous.signal_id == signal_id
        if same_setup and previous.state == candidate.state:
            return False
        if same_setup:
            # Section 26.2's second clause: the phase changed, so this says
            # something the last message did not.
            self._last[market] = _Said(signal_id, candidate.state, at_ns)
            return True

        # A different setup on the same market: section 26.2's third clause
        # needs both the elapsed cooldown and the new touch, and a new signal
        # id is the new touch.
        if at_ns - previous.at_ns < self.cooldown_ns:
            return False

        self._last[market] = _Said(signal_id, candidate.state, at_ns)
        return True
