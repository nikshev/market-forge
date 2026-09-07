"""Provenance and timing carried by every canonical event.

# @trace: REQ-WP-002

PRD section 9 opens with "Every event must include" and then gives EventMeta.
Section 10's models do not include it -- they repeat three of its fields and
drop the other five. ADR-003 resolves that in favour of section 9: a rule beats
an illustration, and embedding makes `ingest_time_ns` and `sequence` impossible
to leave out.

That matters beyond tidiness. Constitution Principle II and PRD section 0.4
forbid conflating the six timestamp kinds, and section 9 forbids any feature
depending on `ingest_time` as market information. Neither rule is checkable if
the field can simply be absent.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EventMeta(BaseModel):
    """Where an event came from, and when -- by two different clocks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    symbol: str = Field(min_length=1)

    #: Assigned by the exchange or chain. The only clock a feature may use.
    event_time_ns: int = Field(ge=0)
    #: When we received it. Never market information -- see PRD section 9.
    ingest_time_ns: int = Field(ge=0)

    sequence: int | None = None
    source_event_id: str | None = None


class ChainMeta(BaseModel):
    """Position of an event within a blockchain.

    Separate from EventMeta rather than optional fields on it: every CEX event
    would otherwise carry four permanently-null columns. PRD section 9 says
    blockchain events "also include" these, which reads as an addition rather
    than a widening.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain_id: int = Field(ge=0)
    block_number: int = Field(ge=0)
    block_time_ns: int = Field(ge=0)
    tx_hash: str = Field(min_length=1)
    tx_index: int = Field(ge=0)
    log_index: int = Field(ge=0)
