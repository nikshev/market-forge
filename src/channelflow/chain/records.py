"""PRD section 18.3's canonical raw chain envelope.

# @trace: REQ-WP-014

    "Every EVM-originated item must preserve enough information for
    deterministic replay... Raw chain records are immutable append-only data."

Section 18.19 gives the four times a chain record carries, and the sentence
that makes them matter:

    "A historical backtest at 12:00:01.500 must not see that swap even though
    block_time is earlier."

On-chain data has a different availability model from a websocket. The block
time is when the event happened; `available_at` is when a strategy was allowed
to use it, and the gap between them is real -- a head arrives, receipts follow,
and only then is the log complete. Treating block time as availability is the
mistake this whole section exists to prevent.
"""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field


class Finality(IntEnum):
    """PRD section 18.4's ladder.

    An `IntEnum` so comparisons read as they mean: `status >= Finality.SAFE` is
    the research default rule 2 states, and ordering is the whole point of the
    ladder.
    """

    SEEN = 0
    HEAD_CONFIRMED = 1
    SAFE = 2
    FINALIZED = 3


class ChainRecord(BaseModel):
    """One log, with everything deterministic replay needs.

    Frozen: section 18.3 says raw chain records are immutable append-only data,
    and ADR-033 depends on it -- a reorg orphans a record and never edits one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain_id: int = Field(ge=1)
    network: str = Field(min_length=1)
    block_number: int = Field(ge=0)
    block_hash: str = Field(min_length=1)
    parent_hash: str = Field(min_length=1)
    block_time_ns: int = Field(ge=0)
    transaction_hash: str = Field(min_length=1)
    transaction_index: int = Field(ge=0)
    log_index: int = Field(ge=0)
    address: str = Field(min_length=1)
    topics: tuple[str, ...] = Field(min_length=1)
    data: str = ""
    removed: bool = False

    #: When the collector first saw it.
    observed_at_ns: int = Field(ge=0)
    #: When a live strategy was allowed to use it (section 18.19).
    available_at_ns: int = Field(ge=0)
    #: When the configured confirmation policy was reached, if it has been.
    safe_at_ns: int | None = None
    #: Set by a reorg. The record's other fields never change (ADR-033).
    orphaned_at_ns: int | None = None

    finality: Finality = Finality.SEEN
    confirmations: int = Field(ge=0, default=0)
    provider: str = Field(min_length=1)
    schema_version: int = Field(ge=1, default=1)

    @property
    def topic0(self) -> str:
        return self.topics[0]

    @property
    def source_event_id(self) -> str:
        """Section 18.4's `source_event_id`: unique within a chain."""
        return f"{self.chain_id}:{self.block_hash}:{self.transaction_index}:{self.log_index}"

    def model_post_init(self, _: object) -> None:
        if self.observed_at_ns < self.block_time_ns:
            raise ValueError(
                f"record observed at {self.observed_at_ns} but its block is timed at "
                f"{self.block_time_ns}: a collector cannot see something before it "
                "happened"
            )
        if self.available_at_ns < self.observed_at_ns:
            raise ValueError(
                f"record available at {self.available_at_ns} but only observed at "
                f"{self.observed_at_ns}: PRD section 18.19 orders these, and a "
                "backtest reading the earlier one would see data the live system "
                "did not have"
            )


class ReorgInvalidation(BaseModel):
    """PRD section 18.4 rule 5's invalidation event.

    Carries the block, not the records: there is no path from here that could
    modify one, even deliberately. The same shape REQ-WP-019's
    `CandidateInvalidation` uses, and for the same reason.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain_id: int = Field(ge=1)
    block_number: int = Field(ge=0)
    orphaned_block_hash: str = Field(min_length=1)
    replacement_block_hash: str | None = None
    detected_at_ns: int = Field(ge=0)
    reason: str = Field(min_length=1)
