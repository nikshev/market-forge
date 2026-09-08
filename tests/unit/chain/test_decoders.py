"""PRD section 18.6's decoder registry (REQ-WP-014)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from channelflow.chain import (
    ChainRecord,
    DecoderRegistry,
    ProtocolEvent,
    RegistryEntry,
)

from .conftest import POOL, record


@dataclass
class SwapDecoder:
    protocol: str = "uniswap_v3"
    version: str = "1.0.0"

    def matches(self, record: ChainRecord, entry: RegistryEntry) -> bool:
        return record.topic0 == "0xtopic0"

    def decode(self, record: ChainRecord, entry: RegistryEntry) -> list[ProtocolEvent]:
        return [
            ProtocolEvent(
                protocol=self.protocol,
                version=self.version,
                name="Swap",
                address=record.address,
                fields={"data": record.data},
                source=record,
            )
        ]


def registry(**overrides: object) -> DecoderRegistry:
    fields: dict[str, object] = {
        "protocol": "uniswap_v3",
        "version": "1.0.0",
        "address": POOL,
        "abi_hash": "0xabi_v1",
        "from_block": 0,
    }
    fields.update(overrides)
    reg = DecoderRegistry()
    reg.register(RegistryEntry(**fields), SwapDecoder())  # type: ignore[arg-type]
    return reg


@pytest.mark.trace("REQ-WP-014")
def test_a_registered_decoder_handles_its_log() -> None:
    """FR-009. The registry must actually work, or fail-closed is trivial."""
    events, failure = registry().decode(record(block=100), observed_abi_hash="0xabi_v1")

    assert failure is None
    assert [e.name for e in events] == ["Swap"]


@pytest.mark.trace("REQ-WP-014")
def test_a_mismatched_abi_hash_fails_closed() -> None:
    """SC-006, FR-010, ADR-034, PRD section 18.6:

        "If an implementation changes unexpectedly, ingestion must fail closed
        for semantic state reconstruction while continuing to retain raw logs."

    A decoder matching on event signature alone would happily decode a proxy
    upgraded to different semantics -- structurally valid events, economically
    wrong, and nothing downstream could tell.
    """
    raw = record(block=100)

    events, failure = registry().decode(raw, observed_abi_hash="0xabi_v2_upgraded")

    assert events == []
    assert failure is not None
    assert "failing closed" in failure.reason
    assert failure.record is raw, "the raw log is retained regardless"


@pytest.mark.trace("REQ-WP-014")
def test_a_log_with_no_registry_entry_produces_no_event_but_keeps_the_record() -> None:
    """FR-011, SC-006. Most logs on a chain are nothing to do with us; that is
    not an error, and the record is still evidence."""
    raw = record(block=100, address="0xSOMETHING_ELSE")

    events, failure = registry().decode(raw)

    assert events == []
    assert failure is not None and failure.record is raw


@pytest.mark.trace("REQ-WP-014")
def test_deployment_ranges_select_between_decoder_versions() -> None:
    """SC-007, FR-009, PRD section 18.6's "deployment range".

    One address, two implementations over time. Selecting by address alone
    would decode the new contract with the old decoder.
    """
    reg = DecoderRegistry()
    reg.register(
        RegistryEntry(
            protocol="uniswap_v3",
            version="1.0.0",
            address=POOL,
            abi_hash="0xabi_v1",
            from_block=0,
            to_block=150,
        ),
        SwapDecoder(version="1.0.0"),
    )
    reg.register(
        RegistryEntry(
            protocol="uniswap_v3",
            version="2.0.0",
            address=POOL,
            abi_hash="0xabi_v2",
            from_block=151,
        ),
        SwapDecoder(version="2.0.0"),
    )

    old = reg.entry_for(record(block=100))
    new = reg.entry_for(record(block=200))

    assert old is not None and old.version == "1.0.0"
    assert new is not None and new.version == "2.0.0"


@pytest.mark.trace("REQ-WP-014")
def test_a_log_before_the_deployment_range_is_not_covered() -> None:
    """FR-009. A contract cannot emit a log before it was deployed, and a
    registry entry that covered earlier blocks would be describing something
    else."""
    reg = registry(from_block=500)

    assert reg.entry_for(record(block=100)) is None


@pytest.mark.trace("REQ-WP-014")
def test_the_chain_package_cannot_consult_a_clock_or_open_a_socket() -> None:
    """SC-010, FR-016.

    The provider protocol is defined and no implementation ships -- the same
    boundary ADR-012 drew for the order book and ADR-018 for the alerter.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "chain"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "time.monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
        for forbidden in ("import requests", "import httpx", "web3", "aiohttp"):
            assert forbidden not in source, f"{module.name} opens a socket: {forbidden!r}"
