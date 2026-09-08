"""PRD section 18.6's ABI and decoder registry.

# @trace: REQ-WP-014

    "Decoder selection is versioned and deterministic... If an implementation
    changes unexpectedly, ingestion must fail closed for semantic state
    reconstruction while continuing to retain raw logs."

Two failure modes are ruled out at once, and ADR-034 separates them. A decoder
matching on event signature alone would happily decode a proxy upgraded to
different semantics -- structurally valid events, economically wrong, and
nothing downstream could tell. Refusing the log entirely would lose the only
evidence of what happened, at exactly the moment it matters most.

So decoding fails closed and retention is unconditional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from channelflow.chain.records import ChainRecord


@dataclass(frozen=True)
class ProtocolEvent:
    """Something a decoder understood."""

    protocol: str
    version: str
    name: str
    address: str
    fields: dict[str, str]
    source: ChainRecord


@dataclass(frozen=True)
class DecodeFailure:
    """Why a log produced no event. The raw record is retained regardless."""

    record: ChainRecord
    reason: str


class ProtocolDecoder(Protocol):
    """PRD section 18.6's protocol, verbatim in shape."""

    protocol: str
    version: str

    def matches(self, record: ChainRecord, entry: RegistryEntry) -> bool: ...

    def decode(self, record: ChainRecord, entry: RegistryEntry) -> list[ProtocolEvent]: ...


@dataclass(frozen=True)
class RegistryEntry:
    """What the registry knows about one deployed contract.

    `abi_hash` is the field that makes fail-closed possible: an upgraded proxy
    keeps its address and changes its ABI, and matching on address alone would
    decode the new contract with the old decoder.
    """

    protocol: str
    version: str
    address: str
    abi_hash: str
    from_block: int
    to_block: int | None = None
    event_signatures: tuple[str, ...] = ()

    def covers(self, record: ChainRecord) -> bool:
        if record.address.lower() != self.address.lower():
            return False
        if record.block_number < self.from_block:
            return False
        return self.to_block is None or record.block_number <= self.to_block


@dataclass
class DecoderRegistry:
    """Deterministic selection by protocol, version and deployment range."""

    entries: list[RegistryEntry] = field(default_factory=list)
    decoders: dict[tuple[str, str], ProtocolDecoder] = field(default_factory=dict)

    def register(self, entry: RegistryEntry, decoder: ProtocolDecoder) -> None:
        self.entries.append(entry)
        self.decoders[(entry.protocol, entry.version)] = decoder

    def entry_for(self, record: ChainRecord) -> RegistryEntry | None:
        """The entry whose deployment range contains this block.

        Ranges are checked in registration order and the first match wins;
        overlapping ranges for one address are a registry error, not something
        to resolve here.
        """
        return next((e for e in self.entries if e.covers(record)), None)

    def decode(
        self, record: ChainRecord, *, observed_abi_hash: str | None = None
    ) -> tuple[list[ProtocolEvent], DecodeFailure | None]:
        """Decode, or say why not. The raw record is the caller's either way."""
        entry = self.entry_for(record)
        if entry is None:
            # Not an error: most logs on a chain are nothing to do with us.
            return [], DecodeFailure(
                record=record, reason="no registry entry covers this address and block"
            )

        if observed_abi_hash is not None and observed_abi_hash != entry.abi_hash:
            # PRD section 18.6's fail-closed. The contract is not what the
            # registry describes, so anything decoded from it would be a guess
            # wearing the shape of a fact.
            return [], DecodeFailure(
                record=record,
                reason=(
                    f"ABI hash {observed_abi_hash} does not match the registry's "
                    f"{entry.abi_hash} for {entry.protocol} {entry.version}; failing "
                    "closed for semantic decoding while the raw log is retained"
                ),
            )

        decoder = self.decoders.get((entry.protocol, entry.version))
        if decoder is None or not decoder.matches(record, entry):
            return [], DecodeFailure(
                record=record,
                reason=f"no decoder matched {entry.protocol} {entry.version}",
            )

        return decoder.decode(record, entry), None
