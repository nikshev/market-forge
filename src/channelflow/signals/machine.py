"""The candidate state machine.

# @trace: REQ-WP-007

One transition table over PRD section 21.2's lifecycle, serving all four
families A to D. Direction and boundary are candidate attributes, so adding a
family adds preconditions rather than states -- ADR-008.

Every move goes through `_advance`, which refuses anything `ALLOWED` does not
list. That is what makes FR-007 -- no skipped steps -- a property of the code
rather than a habit of whoever wrote the branches. A machine that could jump
from touch to confirmed would emit signals that never rejected, and downstream
they would be indistinguishable from real ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.signals.models import ALLOWED, Candidate, CandidateState, Transition
from channelflow.signals.rejection import CloseBackInside, RejectionDetector


class IllegalTransition(RuntimeError):
    """A move the lifecycle does not permit was attempted."""


@dataclass
class SignalMachine:
    """At most one candidate per symbol and timeframe (FR-014).

    Every threshold is an argument. PRD section 13.11 calls its zone defaults
    "research defaults, not proven parameters", and hard-coding them would make
    that statement untrue by omission.
    """

    zone_upper: tuple[float, float] = (0.88, 1.00)
    zone_lower: tuple[float, float] = (0.00, 0.12)
    zone_middle: tuple[float, float] = (0.44, 0.56)
    overshoot_tolerance: float = 0.08
    min_quality: float = 0.5
    slope_threshold: float = 0.05
    expiry_bars: int = 10
    detector: RejectionDetector = field(default_factory=CloseBackInside)

    candidate: Candidate | None = None
    #: FR-018. After a terminal candidate, price must leave every zone before a
    #: new one may open. Without this the machine churns: expire while price is
    #: still in the zone, reopen on the next bar, expire again. Found by a test
    #: that expected an expired candidate and got a freshly opened one.
    _awaiting_zone_exit: bool = False

    def on_bar(self, bar: Bar, channel: ChannelSnapshot | None) -> Candidate | None:
        """Advance by one bar. Returns the live candidate, or None."""
        if channel is None:
            # FR-015: a signal derived from an absent channel is derived from
            # nothing. Neither open nor advance.
            return self.candidate

        if self.candidate is not None and not self.candidate.is_terminal:
            self._progress(bar, channel)
            if self.candidate.is_terminal:
                self._awaiting_zone_exit = True
        elif self._awaiting_zone_exit:
            if not self._in_any_zone(self.position(bar, channel)):
                self._awaiting_zone_exit = False
        else:
            self._maybe_open(bar, channel)

        return self.candidate

    def position(self, bar: Bar, channel: ChannelSnapshot) -> float:
        """PRD section 13.10's normalized coordinate."""
        span = channel.upper_now - channel.lower_now
        if span <= 0:
            return 0.5
        return (float(bar.close) - channel.lower_now) / span

    def _maybe_open(self, bar: Bar, channel: ChannelSnapshot) -> None:
        if channel.quality.score < self.min_quality:
            return

        pos = self.position(bar, channel)
        slope = channel.slope_normalized

        # FR-004: the channel's own direction and quality must justify the
        # setup. PRD section 1.2 puts the edge in the conditions, not the touch.
        if self.zone_upper[0] <= pos <= self.zone_upper[1] + self.overshoot_tolerance:
            if slope > -self.slope_threshold:
                return
            self._open(bar, direction="short", boundary="upper")
        elif self.zone_lower[0] - self.overshoot_tolerance <= pos <= self.zone_lower[1]:
            if slope < self.slope_threshold:
                return
            self._open(bar, direction="long", boundary="lower")
        elif self.zone_middle[0] <= pos <= self.zone_middle[1]:
            if slope <= -self.slope_threshold:
                self._open(bar, direction="short", boundary="middle")
            elif slope >= self.slope_threshold:
                self._open(bar, direction="long", boundary="middle")

    def _open(self, bar: Bar, *, direction: str, boundary: str) -> None:
        transition = Transition(
            from_state=CandidateState.NONE,
            to_state=CandidateState.APPROACH,
            bar_close_time_ns=bar.close_time_ns,
            reason=f"price entered the {boundary} zone in a {direction}-supporting channel",
        )
        self.candidate = Candidate(
            venue=bar.venue,
            symbol=bar.symbol,
            timeframe_ns=bar.timeframe_ns,
            direction=direction,  # type: ignore[arg-type]
            boundary=boundary,  # type: ignore[arg-type]
            state=CandidateState.APPROACH,
            opened_at_ns=bar.close_time_ns,
            bars_since_open=0,
            history=(transition,),
        )

    def _progress(self, bar: Bar, channel: ChannelSnapshot) -> None:
        assert self.candidate is not None
        candidate = self.candidate
        pos = self.position(bar, channel)

        candidate = candidate.model_copy(update={"bars_since_open": candidate.bars_since_open + 1})
        self.candidate = candidate

        if channel.quality.score < self.min_quality:
            self._advance(bar, CandidateState.INVALIDATED, "channel quality collapsed")
            return
        if pos > 1.0 + self.overshoot_tolerance or pos < -self.overshoot_tolerance:
            self._advance(bar, CandidateState.INVALIDATED, "close beyond outer tolerance")
            return
        if candidate.state is CandidateState.APPROACH and self._at_boundary(
            pos, candidate.boundary
        ):
            self._advance(bar, CandidateState.TOUCH, f"reached the {candidate.boundary} boundary")
        elif candidate.state is CandidateState.TOUCH and self.detector.rejected(
            bar, channel, boundary=candidate.boundary, direction=candidate.direction
        ):
            self._advance(
                bar, CandidateState.REJECTION_PENDING, f"rejected by {self.detector.name}"
            )
        elif candidate.state is CandidateState.REJECTION_PENDING and self.detector.rejected(
            bar, channel, boundary=candidate.boundary, direction=candidate.direction
        ):
            self._advance(bar, CandidateState.CONFIRMED, "rejection held for a second bar")

        # Expiry is checked LAST, and only if this bar advanced nothing.
        # `expiry_bars` means "that many bars WITHOUT confirmation" -- so a bar
        # that does confirm is not one of them. Checking first expired a
        # candidate on the very bar that would have confirmed it.
        if (
            self.candidate is not None
            and self.candidate.state is candidate.state
            and self.candidate.bars_since_open >= self.expiry_bars
            and self.candidate.state
            in {CandidateState.APPROACH, CandidateState.TOUCH, CandidateState.REJECTION_PENDING}
        ):
            self._advance(
                bar, CandidateState.EXPIRED, f"no confirmation in {self.expiry_bars} bars"
            )

    def _in_any_zone(self, pos: float) -> bool:
        return (
            self.zone_lower[0] - self.overshoot_tolerance <= pos <= self.zone_lower[1]
            or self.zone_middle[0] <= pos <= self.zone_middle[1]
            or self.zone_upper[0] <= pos <= self.zone_upper[1] + self.overshoot_tolerance
        )

    def _at_boundary(self, pos: float, boundary: str) -> bool:
        if boundary == "upper":
            return pos >= self.zone_upper[1]
        if boundary == "lower":
            return pos <= self.zone_lower[0]
        return self.zone_middle[0] <= pos <= self.zone_middle[1]

    def _advance(self, bar: Bar, to_state: CandidateState, reason: str) -> None:
        assert self.candidate is not None
        current = self.candidate.state
        if to_state not in ALLOWED[current]:
            raise IllegalTransition(
                f"{current.value} -> {to_state.value} is not a legal move; "
                "the lifecycle in PRD section 21.2 has no such edge"
            )
        transition = Transition(
            from_state=current,
            to_state=to_state,
            bar_close_time_ns=bar.close_time_ns,
            reason=reason,
        )
        self.candidate = self.candidate.model_copy(
            update={"state": to_state, "history": (*self.candidate.history, transition)}
        )
