# @trace: REQ-INFRA-007
"""The record hash: its envelope, and that each of its four inputs matters (FR-001, FR-003)."""

from __future__ import annotations

import hashlib
import struct

import pytest

from channelflow.notary.scheme import SCHEME_VERSION, Context, record_hash, record_hash_hex

CONTEXT = Context(config_hash="c" * 64, dataset_ref="d" * 64, code_commit="a" * 40)
RECORD = b"\x01\x02\x03 a record's canonical bytes"


def _frame(payload: bytes) -> bytes:
    return struct.pack("<I", len(payload)) + payload


def _by_hand(kind: str, record: bytes, context: Context, version: int = 1) -> bytes:
    """The envelope of contracts/notary-bundle.md, built from the specification alone."""
    return hashlib.sha256(
        b"CFN"
        + bytes([version])
        + _frame(kind.encode())
        + _frame(record)
        + _frame(context.config_hash.encode())
        + _frame(context.dataset_ref.encode())
        + _frame(context.code_commit.encode())
    ).digest()


@pytest.mark.trace("REQ-INFRA-007")
def test_the_envelope_is_the_one_the_specification_describes() -> None:
    assert SCHEME_VERSION == 1
    assert record_hash("snapshot", RECORD, CONTEXT) == _by_hand("snapshot", RECORD, CONTEXT)


@pytest.mark.trace("REQ-INFRA-007")
def test_the_format_is_pinned_by_a_literal_vector() -> None:
    """A third party's checker is written against this value; it must not move by accident."""
    assert record_hash_hex("snapshot", b"abc", CONTEXT) == PINNED


PINNED = "7e906b9c0fc324e85492f6dbc195699f188ade887cbe3b84f44adb53f0a93c69"


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize("kind", ["snapshot", "decision"])
@pytest.mark.parametrize("changed", ["record", "config_hash", "dataset_ref", "code_commit"])
def test_changing_any_one_of_the_four_inputs_changes_the_hash(kind: str, changed: str) -> None:
    """SC-001: four inputs, for a snapshot and for a decision -- eight tests."""
    base = record_hash(kind, RECORD, CONTEXT)
    if changed == "record":
        other = record_hash(kind, RECORD + b"\x00", CONTEXT)
    else:
        other_context = Context(
            config_hash="e" * 64 if changed == "config_hash" else CONTEXT.config_hash,
            dataset_ref="e" * 64 if changed == "dataset_ref" else CONTEXT.dataset_ref,
            code_commit="b" * 40 if changed == "code_commit" else CONTEXT.code_commit,
        )
        other = record_hash(kind, RECORD, other_context)
    assert other != base


@pytest.mark.trace("REQ-INFRA-007")
def test_the_kind_and_the_scheme_version_are_part_of_the_hash() -> None:
    assert record_hash("snapshot", RECORD, CONTEXT) != record_hash("decision", RECORD, CONTEXT)
    assert record_hash("snapshot", RECORD, CONTEXT) != record_hash(
        "snapshot", RECORD, CONTEXT, version=2
    )


@pytest.mark.trace("REQ-INFRA-007")
def test_a_value_cannot_be_shifted_across_a_frame_boundary() -> None:
    """The `("ab", "c")` versus `("a", "bc")` collision that length prefixes exist to prevent."""
    one = Context(config_hash="ab", dataset_ref="c", code_commit="x")
    two = Context(config_hash="a", dataset_ref="bc", code_commit="x")
    assert record_hash("snapshot", RECORD, one) != record_hash("snapshot", RECORD, two)


@pytest.mark.trace("REQ-INFRA-007")
def test_an_empty_record_differs_from_a_missing_one_and_from_another_empty_field() -> None:
    assert record_hash("snapshot", b"", CONTEXT) != record_hash("snapshot", b"\x00", CONTEXT)
    blank = Context(config_hash="", dataset_ref="d" * 64, code_commit="a" * 40)
    assert record_hash("snapshot", RECORD, blank) != record_hash("snapshot", RECORD, CONTEXT)


@pytest.mark.trace("REQ-INFRA-007")
def test_the_hash_is_a_function_of_its_inputs_alone() -> None:
    """FR-003: not of when, in which process, or in which order the calls were made."""
    first = record_hash("decision", RECORD, CONTEXT)
    record_hash("snapshot", b"something else entirely", CONTEXT)
    again = record_hash("decision", RECORD, Context("c" * 64, "d" * 64, "a" * 40))
    assert first == again
    assert len(first) == 32
    assert record_hash_hex("decision", RECORD, CONTEXT) == first.hex()
