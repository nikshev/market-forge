"""Channel snapshot and quality (PRD section 13.1).

# @trace: REQ-WP-006
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChannelQuality(BaseModel):
    """A score in [0,1], and an honest account of what produced it.

    PRD section 13.9 lists nine submetrics. Three cannot be computed yet --
    forecast calibration needs section 13.8's forecast channel, regime
    compatibility needs section 20's engine, and age needs channel-lifetime
    tracking nothing keeps. ADR-007: the unavailable ones are omitted from the
    average rather than defaulted to a neutral value, because a default would
    move the score toward the middle for a reason no reader could see.

    `contributing` and `unavailable` are carried so a six-part score is never
    silently compared against a later nine-part one as though they meant the
    same thing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    submetrics: dict[str, float]
    contributing: tuple[str, ...]
    unavailable: tuple[str, ...]


class ChannelSnapshot(BaseModel):
    """The channel as it stood at one moment.

    Frozen: PRD section 0.5 forbids rewriting a finalized snapshot, and a value
    that cannot be mutated cannot be rewritten.

    `source_max_event_time_ns <= as_of_ns` is PRD section 13.1's hard invariant
    and the reason this model exists in the shape it does. It is validated here
    as well as in the fitter, so a snapshot constructed by any other route still
    cannot claim to have seen the future.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of_ns: int = Field(ge=0)
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    lookback: int = Field(gt=0)

    center_now: float
    upper_now: float
    lower_now: float
    slope_normalized: float
    width_pct: float

    #: Empty for Baseline A. PRD section 13.7 defines forecasts; fabricating a
    #: plausible-looking list here would be worse than an honest absence.
    forecast_horizons: tuple[float, ...] = ()

    quality: ChannelQuality
    source_max_event_time_ns: int = Field(ge=0)

    def model_post_init(self, _: object) -> None:
        if self.source_max_event_time_ns > self.as_of_ns:
            raise ValueError(
                f"snapshot violates PRD section 13.1: source_max_event_time_ns "
                f"({self.source_max_event_time_ns}) is after as_of_ns ({self.as_of_ns}); "
                "this channel would have seen the future"
            )
