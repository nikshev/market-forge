"""The append-only store of what the chain said, and when we could believe it.

# @trace: REQ-WP-014
# @trace: REQ-BIAS-006

PRD section 18.4's rules, and PRD section 41 rule 6 -- "No using later
corrected/reconstructed DEX state as if known earlier unless audit semantics
explicitly allow it."

ADR-033 is the shape: a reorg orphans a record and never edits or deletes one.
A read as of an instant before the reorg still returns it, because it was
genuinely what was known then. A point-in-time read that hid it would be
reconstructing history rather than reporting it -- which is exactly what rule 6
forbids, and what makes a replayed backtest disagree with the live system in a
direction that looks like improvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from channelflow.chain.records import ChainRecord, Finality, ReorgInvalidation


class FinalizedBlockCannotReorg(ValueError):
    """A reorg claimed to remove a block that had reached FINALIZED.

    Finality is the claim that this cannot happen; a chain contradicting it is
    a bug or an attack, and either way not something to absorb silently.
    """


@dataclass(frozen=True)
class FinalityPolicy:
    """PRD section 18.4: "The exact mapping is chain-specific and configurable."

    Depths, not times: a chain's confirmation guarantee is counted in blocks,
    and a wall-clock mapping would drift with block times.
    """

    head_confirmed_depth: int = 1
    safe_depth: int = 12
    finalized_depth: int = 64

    def status_for(self, confirmations: int) -> Finality:
        if confirmations >= self.finalized_depth:
            return Finality.FINALIZED
        if confirmations >= self.safe_depth:
            return Finality.SAFE
        if confirmations >= self.head_confirmed_depth:
            return Finality.HEAD_CONFIRMED
        return Finality.SEEN


@dataclass
class ChainLedger:
    """Append-only. Nothing here removes or edits a record."""

    policy: FinalityPolicy = field(default_factory=FinalityPolicy)
    records: list[ChainRecord] = field(default_factory=list)
    invalidations: list[ReorgInvalidation] = field(default_factory=list)

    def append(self, record: ChainRecord) -> ChainRecord:
        self.records.append(record)
        return record

    def advance(self, *, head_block: int, at_ns: int) -> None:
        """Recompute finality as the head moves.

        Statuses never regress: a record that reached SAFE stays there even if
        a later call passes a lower head, because a status that could go
        backwards is not a guarantee anyone can act on.
        """
        for index, record in enumerate(self.records):
            confirmations = max(0, head_block - record.block_number)
            status = self.policy.status_for(confirmations)
            if status <= record.finality:
                # Never regress. A record that reached SAFE stays there even if
                # a later call passes a lower head -- a status that could go
                # backwards is not a guarantee anyone can act on.
                #
                # The confirmation count still rises: it is information even
                # when the status has not moved.
                if confirmations > record.confirmations:
                    self.records[index] = record.model_copy(update={"confirmations": confirmations})
                continue
            self.records[index] = record.model_copy(
                update={
                    "finality": status,
                    "confirmations": confirmations,
                    "safe_at_ns": record.safe_at_ns
                    if record.safe_at_ns is not None
                    else (at_ns if status >= Finality.SAFE else None),
                }
            )

    def reorg(
        self,
        *,
        chain_id: int,
        block_number: int,
        orphaned_block_hash: str,
        at_ns: int,
        reason: str,
        replacement_block_hash: str | None = None,
    ) -> ReorgInvalidation:
        """PRD section 18.4 rule 5. Orphans, never edits (ADR-033)."""
        affected = [
            (i, r)
            for i, r in enumerate(self.records)
            if r.chain_id == chain_id and r.block_hash == orphaned_block_hash
        ]
        for _, record in affected:
            if record.finality is Finality.FINALIZED:
                raise FinalizedBlockCannotReorg(
                    f"block {orphaned_block_hash} reached FINALIZED and cannot be "
                    "reorganised; finality is the claim that this cannot happen"
                )

        for index, record in affected:
            # Only `orphaned_at_ns` is set. Every other field is what it was,
            # so a read as of an earlier instant returns the record unchanged.
            self.records[index] = record.model_copy(update={"orphaned_at_ns": at_ns})

        invalidation = ReorgInvalidation(
            chain_id=chain_id,
            block_number=block_number,
            orphaned_block_hash=orphaned_block_hash,
            replacement_block_hash=replacement_block_hash,
            detected_at_ns=at_ns,
            reason=reason,
        )
        self.invalidations.append(invalidation)
        return invalidation

    def as_of(self, at_ns: int, *, require: Finality = Finality.SEEN) -> list[ChainRecord]:
        """What a consumer at `at_ns` was allowed to see.

        Filtered by `available_at`, never by block time (PRD section 18.19).
        An orphaned record is still returned when the read predates the reorg:
        it was genuinely what was known then, and hiding it would be
        reconstructing history.
        """
        visible: list[ChainRecord] = []
        for record in self.records:
            if record.available_at_ns > at_ns:
                continue
            if record.orphaned_at_ns is not None and record.orphaned_at_ns <= at_ns:
                continue
            if require > Finality.SEEN:
                if record.safe_at_ns is None or record.safe_at_ns > at_ns:
                    continue
                if record.finality < require:
                    continue
            visible.append(record)
        return sorted(
            visible,
            key=lambda r: (r.block_number, r.transaction_index, r.log_index),
        )
