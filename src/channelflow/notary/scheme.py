"""The record hash and the batch tree: pure functions, no I/O (REQ-INFRA-007).

# @trace: REQ-INFRA-007

The format is specified for third parties in `specs/143-notarize-final-records/contracts/
notary-bundle.md`; this module is that specification in code. Scheme version 1.

**The record hash** binds four inputs -- the record's canonical bytes, the config hash, the
input dataset reference and the code commit -- under a kind and a scheme version, so that a
change of scheme can never produce a value that collides with an older one. Every value is
length-prefixed with the lakehouse's own framing, because a separator can be forged by a value
that contains it: `("ab", "c")` and `("a", "bc")` must not share a hash.

**The tree** is RFC 9162 §2.1 with SHA-256: a one-byte prefix separates a leaf from an interior
node (without it an interior node could be presented as a leaf), the last node is not duplicated
(which would let two different lists share a root), and the inclusion proof is verified with the
RFC's own algorithm. Nothing here is invented; a reader can check it against the RFC.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.lakehouse.schema import length_prefixed

SCHEME_VERSION = 1
_MAGIC = b"CFN"
_LEAF = b"\x00"
_NODE = b"\x01"


@dataclass(frozen=True)
class Context:
    """The three bindings besides the record itself. All three are text."""

    config_hash: str
    dataset_ref: str
    code_commit: str


def record_hash(
    kind: str, record: bytes, context: Context, *, version: int = SCHEME_VERSION
) -> bytes:
    """SHA-256 over the envelope of scheme `version`."""
    digest = hashlib.sha256()
    digest.update(_MAGIC)
    digest.update(bytes([version]))
    digest.update(length_prefixed(kind.encode()))
    digest.update(length_prefixed(record))
    digest.update(length_prefixed(context.config_hash.encode()))
    digest.update(length_prefixed(context.dataset_ref.encode()))
    digest.update(length_prefixed(context.code_commit.encode()))
    return digest.digest()


def record_hash_hex(
    kind: str, record: bytes, context: Context, *, version: int = SCHEME_VERSION
) -> str:
    return record_hash(kind, record, context, version=version).hex()


def leaf_hash(item: bytes) -> bytes:
    return hashlib.sha256(_LEAF + item).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(_NODE + left + right).digest()


def _split(n: int) -> int:
    """The largest power of two strictly less than `n` (n >= 2)."""
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_root(items: Sequence[bytes]) -> bytes:
    """MTH of RFC 9162 §2.1.1 over `items` in the order given."""
    if not items:
        raise ValueError("an empty tree has no root; a batch holds at least one record")
    if len(items) == 1:
        return leaf_hash(items[0])
    k = _split(len(items))
    return node_hash(merkle_root(items[:k]), merkle_root(items[k:]))


def inclusion_proof(items: Sequence[bytes], index: int) -> list[bytes]:
    """PATH(index, items) of RFC 9162 §2.1.3.1: the sibling hashes from leaf to root."""
    if not items:
        raise ValueError("an empty tree has no proofs")
    if not 0 <= index < len(items):
        raise IndexError(f"leaf {index} is outside a tree of {len(items)}")
    if len(items) == 1:
        return []
    k = _split(len(items))
    if index < k:
        return [*inclusion_proof(items[:k], index), merkle_root(items[k:])]
    return [*inclusion_proof(items[k:], index - k), merkle_root(items[:k])]


def verify_inclusion(
    item: bytes, index: int, size: int, path: Sequence[bytes], root: bytes
) -> bool:
    """RFC 9162 §2.1.3.2: does `item` sit at `index` of a tree of `size` leaves with this root?"""
    if size < 1 or not 0 <= index < size:
        return False
    fn, sn = index, size - 1
    result = leaf_hash(item)
    for sibling in path:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            result = node_hash(sibling, result)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            result = node_hash(result, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and result == root
