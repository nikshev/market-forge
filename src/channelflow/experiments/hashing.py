"""Hashing the two components that are not already hashes.

# @trace: REQ-REPRO-001

PRD §0 item 13 asks for a versioned dataset and a config. The lakehouse already
names a dataset -- [[ADR-053]] -- but a run reads several tables, and a config is
a nested mapping with no schema at all. Both need turning into one string each,
and both need the same property: the same input gives the same output in any
process, on any machine, after any dependency upgrade.

`json.dumps(..., sort_keys=True)` almost does it and fails on two things worth
being careful about. It renders `1` and `1.0` identically in some encoders and
not others, and it renders `True` as `true` -- which collides with the string
`"true"`. A config where a flag was quoted by accident would hash the same as
one where it was not, and the two configure different runs.

So the encoding here is length-prefixed and type-tagged, like the lakehouse's
row encoding and for the same reasons. It is not the lakehouse's function
because that one encodes a flat row against a declared schema, and this one
encodes an arbitrary nested structure that has none.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Mapping, Sequence

#: What a config may hold. Anything else is a refusal rather than a `repr()`:
#: `repr` of an object includes its memory address on some types, which would
#: make a config hash different on every run for a reason nobody would find.
ConfigValue = (
    Mapping[str, "ConfigValue"] | Sequence["ConfigValue"] | str | int | float | bool | None
)

_TAG_MAP = b"m"
_TAG_SEQ = b"q"
_TAG_STR = b"s"
_TAG_INT = b"i"
_TAG_FLOAT = b"f"
_TAG_BOOL = b"b"
_TAG_NULL = b"n"


class UnhashableConfig(TypeError):
    """A config holds something with no canonical encoding."""


def config_hash(config: Mapping[str, object]) -> str:
    """A configuration's identity, independent of key order.

    Mappings are encoded with their keys sorted, so two configs that differ only
    in how they were written down are the same config. Sequences keep their
    order, because a list of lookbacks is not a set.
    """
    digest = hashlib.sha256()
    digest.update(_encode(config, path="config"))
    return digest.hexdigest()


def dataset_reference(snapshots: Mapping[str, tuple[int, str]]) -> str:
    """One dataset identity over several tables.

    `snapshots` maps a table name to the snapshot id it was read at and that
    snapshot's content hash. Both are recorded: the id is how a reader finds the
    data again, and the hash is what says it is the same data -- an id alone
    would be a pointer, and a pointer to a table someone rebuilt is not a
    dataset.

    Sorted by table name, so a run that listed its tables in a different order
    reads the same data and has the same dataset identity.
    """
    if not snapshots:
        raise ValueError(
            "a run over no tables has no dataset to be reproducible from; an empty "
            "reference would record that it does"
        )
    digest = hashlib.sha256()
    for table in sorted(snapshots):
        snapshot_id, content_hash = snapshots[table]
        if snapshot_id < 1:
            raise ValueError(
                f"{table} is referenced at snapshot {snapshot_id}; snapshots are "
                "numbered from one and a zero here means nobody looked"
            )
        if not content_hash:
            raise ValueError(
                f"{table} is referenced at snapshot {snapshot_id} with no content "
                "hash; the id alone is a pointer, and a pointer to a table someone "
                "rebuilt is not a dataset"
            )
        for part in (table, str(snapshot_id), content_hash):
            payload = part.encode()
            digest.update(struct.pack("<I", len(payload)))
            digest.update(payload)
    return digest.hexdigest()


def _encode(value: object, *, path: str) -> bytes:
    """One value's canonical bytes, tagged by type and length-prefixed.

    `bool` is checked before `int` because Python says `isinstance(True, int)`,
    and a config where `enabled: true` hashed the same as `enabled: 1` would let
    a type change pass as no change.
    """
    if value is None:
        return _TAG_NULL
    if isinstance(value, bool):
        return _TAG_BOOL + (b"\x01" if value else b"\x00")
    if isinstance(value, int):
        return _TAG_INT + _framed(str(value).encode())
    if isinstance(value, float):
        # The IEEE-754 bytes rather than a rendering: `repr(0.1)` is stable in
        # CPython and is not a cross-language contract, and `-0.0` renders
        # differently from `0.0` while comparing equal.
        return _TAG_FLOAT + struct.pack("<d", value)
    if isinstance(value, str):
        return _TAG_STR + _framed(value.encode("utf-8"))
    if isinstance(value, Mapping):
        parts = [_TAG_MAP]
        for key in sorted(value):
            if not isinstance(key, str):
                raise UnhashableConfig(
                    f"{path} has a non-string key {key!r}; YAML and JSON configs have "
                    "string keys, and sorting a mixed set is not defined"
                )
            parts.append(_framed(key.encode("utf-8")))
            parts.append(_framed(_encode(value[key], path=f"{path}.{key}")))
        return _framed(b"".join(parts))
    if isinstance(value, Sequence):
        parts = [_TAG_SEQ]
        for index, item in enumerate(value):
            parts.append(_framed(_encode(item, path=f"{path}[{index}]")))
        return _framed(b"".join(parts))
    raise UnhashableConfig(
        f"{path} holds {type(value).__name__}, which has no canonical encoding. "
        "Falling back to repr() would put a memory address in the hash on some "
        "types, and the config would look different on every run"
    )


def _framed(payload: bytes) -> bytes:
    return struct.pack("<I", len(payload)) + payload
