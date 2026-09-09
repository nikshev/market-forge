"""PRD section 31's `signals:` block, as a unit a backtest can run.

# @trace: REQ-US-005

    signals:
      upper_rejection_short:
        enabled: true
        min_channel_quality: 0.70
        upper_zone_start: 0.88
        overshoot_tolerance: 0.08
        confirmation_bars: 2
        min_score: 75
        cooldown_bars: 8

REQ-US-005 asks to backtest `upper_rejection_short` separately from
`middle_continuation_short`. Both already exist as candidate shapes -- the engine
opens upper-zone shorts and middle-zone shorts today -- and what was missing is
the family as a unit of configuration and reporting.

The restriction is on what may *open*, never on what is reported. The engine
tracks one candidate at a time, so a middle-zone setup occupies the machine and
the upper-zone setup two bars later never opens; filtering a finished report
would leave that interference in the counts while looking clean.

Configuration only. PRD section 25.2 forbids a separate backtest implementation
and Constitution Principle VII says live and replay are the same code, so a
transition rule here would be a second engine with a nicer name. A test asserts
this file contains none.

Three of section 31's fields are deliberately absent: `confirmation_bars` is the
engine's own two-bar rule, `min_score` belongs to REQ-SCORE-001's threshold, and
`cooldown_bars` has no engine support. Carrying them here would describe
behaviour that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from channelflow.signals import SignalMachine


@dataclass(frozen=True)
class SetupFamily:
    """One named setup, and the thresholds it runs under."""

    name: str
    boundary: Literal["upper", "lower", "middle"]
    direction: Literal["long", "short"]
    zone: tuple[float, float]
    min_quality: float = 0.70
    overshoot_tolerance: float = 0.08
    slope_threshold: float = 0.05
    expiry_bars: int = 10

    def __post_init__(self) -> None:
        low, high = self.zone
        if not 0.0 <= low <= high <= 1.0:
            raise ValueError(
                f"family {self.name!r} has zone {self.zone}, which is inverted or outside "
                "[0, 1]; it would match nothing and report zero candidates, reading as "
                "'no setups found' rather than as 'this family cannot open one'"
            )
        if not 0.0 <= self.min_quality <= 1.0:
            raise ValueError(f"family {self.name!r} has a quality floor outside [0, 1]")

    def machine(self) -> SignalMachine:
        """A production `SignalMachine` restricted to this family."""
        zones = {
            "upper": {"zone_upper": self.zone},
            "lower": {"zone_lower": self.zone},
            "middle": {"zone_middle": self.zone},
        }[self.boundary]
        return SignalMachine(
            min_quality=self.min_quality,
            overshoot_tolerance=self.overshoot_tolerance,
            slope_threshold=self.slope_threshold,
            expiry_bars=self.expiry_bars,
            opens=((self.boundary, self.direction),),
            **zones,  # type: ignore[arg-type]
        )

    def configuration(self) -> dict[str, str]:
        return {
            "family": self.name,
            "boundary": self.boundary,
            "direction": self.direction,
            "zone": f"{self.zone[0]}-{self.zone[1]}",
            "min_quality": str(self.min_quality),
            "overshoot_tolerance": str(self.overshoot_tolerance),
        }


#: Section 31's own numbers, and the only family the PRD writes out in full.
UPPER_REJECTION_SHORT = SetupFamily(
    name="upper_rejection_short",
    boundary="upper",
    direction="short",
    zone=(0.88, 1.00),
    min_quality=0.70,
    overshoot_tolerance=0.08,
)

#: Section 31 names no thresholds for this one, so it takes PRD section 13.11's
#: middle-zone research defaults -- the same numbers the engine already uses.
MIDDLE_CONTINUATION_SHORT = SetupFamily(
    name="middle_continuation_short",
    boundary="middle",
    direction="short",
    zone=(0.44, 0.56),
    min_quality=0.70,
)

FAMILIES: dict[str, SetupFamily] = {
    UPPER_REJECTION_SHORT.name: UPPER_REJECTION_SHORT,
    MIDDLE_CONTINUATION_SHORT.name: MIDDLE_CONTINUATION_SHORT,
}
