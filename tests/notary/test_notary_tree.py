# @trace: REQ-INFRA-007
"""The batch tree is RFC 9162's, with SHA-256, and its proofs verify (plan decision 6)."""

from __future__ import annotations

import hashlib

import pytest

from channelflow.notary.scheme import (
    inclusion_proof,
    leaf_hash,
    merkle_root,
    node_hash,
    verify_inclusion,
)


def _h(i: int) -> bytes:
    return hashlib.sha256(f"record-{i}".encode()).digest()


# ---- an independent implementation, written from the RFC text and nothing else -------------------


def ref_mth(items: list[bytes]) -> bytes:
    """RFC 9162 §2.1.1: a leaf is HASH(0x00 || d); else split at the largest power of two < n."""
    n = len(items)
    if n == 1:
        return hashlib.sha256(b"\x00" + items[0]).digest()
    k = 1
    while k * 2 < n:
        k *= 2
    return hashlib.sha256(b"\x01" + ref_mth(items[:k]) + ref_mth(items[k:])).digest()


def ref_path(m: int, items: list[bytes]) -> list[bytes]:
    """RFC 9162 §2.1.3.1: PATH(m, D[n])."""
    n = len(items)
    if n == 1:
        return []
    k = 1
    while k * 2 < n:
        k *= 2
    if m < k:
        return ref_path(m, items[:k]) + [ref_mth(items[k:])]
    return ref_path(m - k, items[k:]) + [ref_mth(items[:k])]


def ref_verify(leaf: bytes, index: int, size: int, path: list[bytes], root: bytes) -> bool:
    """RFC 9162 §2.1.3.2, step by step."""
    if index >= size:
        return False
    fn, sn = index, size - 1
    r = hashlib.sha256(b"\x00" + leaf).digest()
    for p in path:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = hashlib.sha256(b"\x01" + p + r).digest()
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = hashlib.sha256(b"\x01" + r + p).digest()
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


# ---- the tests -----------------------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize("n", range(1, 18))
def test_the_root_equals_the_independent_implementation(n: int) -> None:
    items = [_h(i) for i in range(n)]
    assert merkle_root(items) == ref_mth(items)


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize("n", range(1, 18))
def test_every_leaf_of_every_size_has_the_rfc_path_and_verifies(n: int) -> None:
    items = [_h(i) for i in range(n)]
    root = merkle_root(items)
    for index in range(n):
        path = inclusion_proof(items, index)
        assert path == ref_path(index, items)
        assert verify_inclusion(items[index], index, n, path, root)
        assert ref_verify(items[index], index, n, path, root)


@pytest.mark.trace("REQ-INFRA-007")
def test_a_proof_fails_for_a_flipped_leaf_path_index_or_size() -> None:
    items = [_h(i) for i in range(11)]
    root = merkle_root(items)
    path = inclusion_proof(items, 6)
    assert verify_inclusion(items[6], 6, 11, path, root)

    assert not verify_inclusion(_h(99), 6, 11, path, root)  # another leaf
    flipped = [bytes([path[0][0] ^ 1]) + path[0][1:], *path[1:]]
    assert not verify_inclusion(items[6], 6, 11, flipped, root)  # a bit of the path
    assert not verify_inclusion(items[6], 7, 11, path, root)  # the wrong position
    # A size that changes the tree's shape fails. (Sizes 11 and 12 give leaf 6 the same shape --
    # the leaf is in the left eight either way -- and RFC 9162's algorithm accepts that; the root
    # still has to match, and it does only for the tree the proof was made from.)
    assert not verify_inclusion(items[6], 6, 7, path, root)
    assert not verify_inclusion(items[6], 6, 5, path, root)
    assert not verify_inclusion(items[6], 6, 11, path[:-1], root)  # a shortened path
    assert not verify_inclusion(items[6], 6, 11, path, _h(0))  # another root
    assert not verify_inclusion(items[6], 11, 11, path, root)  # an index outside the tree


@pytest.mark.trace("REQ-INFRA-007")
def test_an_interior_node_cannot_pass_as_a_leaf() -> None:
    """The second-preimage attack the 0x00 / 0x01 prefixes exist to stop."""
    items = [_h(i) for i in range(4)]
    root = merkle_root(items)
    forged_leaf = node_hash(leaf_hash(items[0]), leaf_hash(items[1]))  # an interior node's value
    # Presented as a one-leaf tree, the interior node must not reproduce the real root's subtree.
    assert merkle_root([forged_leaf]) != node_hash(leaf_hash(items[0]), leaf_hash(items[1]))
    assert not verify_inclusion(
        forged_leaf, 0, 2, [node_hash(leaf_hash(items[2]), leaf_hash(items[3]))], root
    )


@pytest.mark.trace("REQ-INFRA-007")
def test_the_tree_is_a_function_of_the_ordered_list_and_an_empty_tree_is_refused() -> None:
    a, b = _h(1), _h(2)
    assert merkle_root([a, b]) != merkle_root([b, a])
    with pytest.raises(ValueError, match="empty"):
        merkle_root([])
    with pytest.raises(ValueError, match="empty"):
        inclusion_proof([], 0)
    with pytest.raises(IndexError):
        inclusion_proof([a], 1)
