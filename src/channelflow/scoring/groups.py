"""PRD section 22.1's six feature groups and their caps.

# @trace: REQ-SCORE-001

    channel_structure       0..30
    rejection_quality       0..20
    order_flow_confirmation 0..20
    volume_confirmation     0..10
    derivatives_context     0..10
    defi_crossvenue_context 0..10

The caps sum to 100, which is what makes the raw score a score out of 100
rather than a total that happens to look like a percentage.

Contributions are supplied rather than computed here. Each family's arithmetic
already lives in its own package -- channel quality in `channels`, order flow in
`features`, volume in `volume`, derivatives in `derivatives`, DeFi and
cross-venue in `dex` and `crossvenue`. A scoring engine that reached into all
six would own none of them and depend on all of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Group(StrEnum):
    """Section 22.1's groups, by the PRD's own names."""

    CHANNEL_STRUCTURE = "channel_structure"
    REJECTION_QUALITY = "rejection_quality"
    ORDER_FLOW = "order_flow_confirmation"
    VOLUME = "volume_confirmation"
    DERIVATIVES = "derivatives_context"
    DEFI_CROSSVENUE = "defi_crossvenue_context"


#: The caps, verbatim from section 22.1.
GROUP_CAPS: dict[Group, float] = {
    Group.CHANNEL_STRUCTURE: 30.0,
    Group.REJECTION_QUALITY: 20.0,
    Group.ORDER_FLOW: 20.0,
    Group.VOLUME: 10.0,
    Group.DERIVATIVES: 10.0,
    Group.DEFI_CROSSVENUE: 10.0,
}


class ContributionOutOfRange(ValueError):
    """A group scored outside `0..cap`."""


@dataclass(frozen=True)
class GroupContribution:
    """What one family contributed, and which factors made it up.

    Refused rather than clipped when it exceeds its cap: clipping turns a
    caller's mistake into a maximum score, and the group then reads as a perfect
    one with nothing downstream saying the value was altered on the way in.

    A dataclass rather than a model, so `ContributionOutOfRange` reaches the
    caller as itself. Wrapped in a validation error it would be caught by
    whatever already handles malformed input, and a scoring mistake would be
    handled as a parsing one.
    """

    group: Group
    value: float
    #: The named factors behind the number -- section 22.4's explainability
    #: needs them, and a contribution nobody can decompose explains nothing.
    factors: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        cap = GROUP_CAPS[self.group]
        if not 0.0 <= self.value <= cap:
            raise ContributionOutOfRange(
                f"group {self.group.value!r} scored {self.value}, outside its "
                f"section 22.1 range 0..{cap}"
            )

    @property
    def cap(self) -> float:
        return GROUP_CAPS[self.group]
