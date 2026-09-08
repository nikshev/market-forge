"""What a training row is made of (PRD section 24.1).

# @trace: REQ-WP-017

Section 24.1's feature snapshot table, column for column:

    entity, as_of_time, feature_name/version, value,
    source_max_event_time, computed_at

with its invariant, `source_max_event_time <= as_of_time`, enforced at
construction rather than checked later. The table itself is unbuilt (PRD
section 29), so these live in memory -- but the shape matches, so persistence
later is a change of source, not of meaning.

Section 24.2 is the rule the `Row` exists to keep:

    Labels may use future data. Features may not.

So a row carries four distinct times, and conflating the last two is exactly
PRD section 41 rule 3:

    as_of_ns              what the features knew
    source_max_event_ns   the latest event any of them saw
    horizon_end_ns        how far the label looked
    label_available_ns    when the label could first be known
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: PRD section 23.5A's Target E.
LabelClass = Literal["MAX", "MIN", "NO_TURN"]


class FeatureSnapshot(BaseModel):
    """One feature's value, as of one instant."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity: str = Field(min_length=1)
    as_of_ns: int = Field(ge=0)
    feature_name: str = Field(min_length=1)
    feature_version: int = Field(ge=1)
    value: float
    #: The latest event that fed this value. PRD section 24.1's invariant is
    #: about this field, and it is the only thing that distinguishes an honest
    #: snapshot from one computed with hindsight and stamped with an old date.
    source_max_event_ns: int = Field(ge=0)
    #: Whether every bar this value derives from had closed by `as_of_ns`.
    #: PRD section 41 rule 4 says no using a final daily high or low before the
    #: daily close; this generalizes it to any timeframe.
    from_finalized_bars: bool = True

    def model_post_init(self, _: object) -> None:
        if self.source_max_event_ns > self.as_of_ns:
            raise ValueError(
                f"snapshot {self.feature_name!r} violates PRD section 24.1: "
                f"source_max_event_time ({self.source_max_event_ns}) is after "
                f"as_of_time ({self.as_of_ns}); this feature saw the future"
            )


class Label(BaseModel):
    """A fact about what happened after `t`, and when it became knowable.

    PRD section 41 rule 3 permits a future-requiring pivot only when "the
    feature availability time is shifted to confirmation time". For a turning
    point that is REQ-WP-019's `known_at`, and `available_ns` is where it goes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label_class: LabelClass
    horizon_end_ns: int = Field(ge=0)
    #: When the system could first have known this. Never the extremum's own
    #: time -- that is the leak the rule exists to prevent.
    available_ns: int = Field(ge=0)
    extremum_time_ns: int | None = None

    def model_post_init(self, _: object) -> None:
        if self.extremum_time_ns is not None and self.available_ns < self.extremum_time_ns:
            raise ValueError(
                f"label available at {self.available_ns} but its extremum occurred at "
                f"{self.extremum_time_ns}: PRD section 13A.1 requires the reverse"
            )


class Row(BaseModel):
    """Features as of `t`, and a label about after `t`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity: str = Field(min_length=1)
    as_of_ns: int = Field(ge=0)
    features: dict[str, float]
    source_max_event_ns: int = Field(ge=0)
    label: Label

    def model_post_init(self, _: object) -> None:
        if self.source_max_event_ns > self.as_of_ns:
            raise ValueError(
                f"row at {self.as_of_ns} carries a feature sourced from "
                f"{self.source_max_event_ns}: PRD section 24.2 forbids a feature "
                "after t"
            )
        if self.label.horizon_end_ns <= self.as_of_ns:
            raise ValueError(
                f"label horizon ends at {self.label.horizon_end_ns}, at or before the "
                f"row's own time {self.as_of_ns}: a label about the past is not a target"
            )
