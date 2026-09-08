"""PRD section 13A.19's canonical models.

# @trace: REQ-WP-019
# @trace: REQ-NRT-B
# @trace: REQ-NRT-C

Section 13A.1 is the rule these exist to carry:

    extremum_time  when the price made the high or low
    known_at       when the system was first legally able to say so

and `extremum_time != known_at` is expected. Its example is worth keeping in
view: a high at 10:00, a reversal threshold crossed at 10:30, and "any backtest
that acts on the 10:00 label before 10:30 is invalid".

So `ConfirmedExtremum` refuses to exist with `known_at < extremum_time`. Test C
then checks a property the type enforces rather than a convention the code is
trusted to follow.

Frozen, all of them: section 13A.19 ends "All models are immutable after
finalization", and Test B requires that an invalidated candidate's original
record be unchanged. A value that cannot be mutated cannot be rewritten.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExtremumType = Literal["HIGH", "LOW"]

#: Namespace for candidate and extremum ids. Derived rather than random, for
#: the reasons ADR-017 gives: a replay that generated fresh ids would produce
#: different records from identical input, all of them looking correct.
EXTREMUM_NAMESPACE = uuid.UUID("2b9c7e04-5a13-53d6-8f27-c4a1e9b60d75")


def _derived_id(*parts: object) -> uuid.UUID:
    return uuid.uuid5(EXTREMUM_NAMESPACE, "|".join(str(p) for p in parts))


class ExtremumCandidate(BaseModel):
    """A running high or low, and when it was observed.

    `candidate_time` is when the price occurred; `observed_at` is the bar the
    observation was made on. They differ for the same reason the confirmed
    pair does.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: uuid.UUID
    instrument_id: str = Field(min_length=1)
    venue_scope: str = Field(min_length=1)
    timeframe_ns: int = Field(gt=0)
    candidate_type: ExtremumType
    candidate_time_ns: int = Field(ge=0)
    observed_at_ns: int = Field(ge=0)
    price: Decimal = Field(gt=0)
    method: str = Field(min_length=1)
    structural_score: float = Field(ge=0.0, le=1.0)
    channel_position: float | None = None
    data_quality: str = Field(min_length=1)

    @classmethod
    def create(
        cls,
        *,
        instrument_id: str,
        venue_scope: str,
        timeframe_ns: int,
        candidate_type: ExtremumType,
        candidate_time_ns: int,
        observed_at_ns: int,
        price: Decimal,
        method: str,
        structural_score: float,
        data_quality: str = "ok",
        channel_position: float | None = None,
    ) -> ExtremumCandidate:
        return cls(
            candidate_id=_derived_id(
                instrument_id, venue_scope, timeframe_ns, candidate_type, candidate_time_ns
            ),
            instrument_id=instrument_id,
            venue_scope=venue_scope,
            timeframe_ns=timeframe_ns,
            candidate_type=candidate_type,
            candidate_time_ns=candidate_time_ns,
            observed_at_ns=observed_at_ns,
            price=price,
            method=method,
            structural_score=structural_score,
            data_quality=data_quality,
            channel_position=channel_position,
        )

    def model_post_init(self, _: object) -> None:
        if self.observed_at_ns < self.candidate_time_ns:
            raise ValueError(
                f"candidate observed at {self.observed_at_ns} but its price occurred at "
                f"{self.candidate_time_ns}: nothing can be observed before it happens"
            )


class ConfirmedExtremum(BaseModel):
    """A candidate whose reversal crossed the threshold.

    The two timestamps and the lag between them are the whole point (PRD
    section 13A.1).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    extremum_id: uuid.UUID
    instrument_id: str = Field(min_length=1)
    timeframe_ns: int = Field(gt=0)
    extremum_type: ExtremumType
    extremum_time_ns: int = Field(ge=0)
    known_at_ns: int = Field(ge=0)
    price: Decimal = Field(gt=0)
    confirmation_method: str = Field(min_length=1)
    confirmation_lag_bars: int = Field(ge=0)
    reversal_bps: float = Field(ge=0.0)
    #: The threshold in force at `known_at`, stored rather than recomputable.
    #: Recomputing it later -- for a report, a chart or a backtest -- is how a
    #: point-in-time value silently becomes a hindsight one.
    threshold_bps: float = Field(gt=0.0)
    prominence_bps: float | None = None
    prominence_atr: float | None = None
    channel_class: str | None = None
    source_candidate_id: uuid.UUID | None = None

    @classmethod
    def create(cls, **fields: object) -> ConfirmedExtremum:
        return cls(
            extremum_id=_derived_id(
                fields["instrument_id"],
                fields["timeframe_ns"],
                fields["extremum_type"],
                fields["extremum_time_ns"],
            ),
            **fields,  # type: ignore[arg-type]
        )

    def model_post_init(self, _: object) -> None:
        # PRD section 13A.28 Test C, as a constructor precondition.
        if self.known_at_ns < self.extremum_time_ns:
            raise ValueError(
                f"known_at {self.known_at_ns} precedes extremum_time "
                f"{self.extremum_time_ns}: PRD section 13A.1 requires "
                "known_at >= extremum_time, and a record claiming otherwise would "
                "let a backtest act on a label before it could be known"
            )


class CandidateInvalidation(BaseModel):
    """Test B: an invalidation is a new record, never an edit.

    Carrying the candidate id rather than the candidate means the original is
    untouched by construction -- there is no path from here that could modify
    it even if someone tried.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: uuid.UUID
    invalidated_at_ns: int = Field(ge=0)
    reason: str = Field(min_length=1)
