"""PRD §35.3's repaint regression, as a harness every model runs through.

# @trace: REQ-NRT-REPAINT

§35.3 calls it the *critical test*:

    1. Feed bars one at a time.
    2. Store channel snapshots.
    3. Continue feeding future bars.
    4. Assert all previous snapshots unchanged.

**Two different things can make step 4 fail, and only one of them is what the
section is really about.**

A stored snapshot can change because something *mutated* it. Measured on this
codebase, that is nearly impossible already: `ChannelSnapshot` is frozen and
every field is immutable by type -- `int`, `str`, `float`, `tuple`, and a frozen
`ChannelQuality`. There is no list and no dict to reach into, plain assignment
raises, and only `object.__setattr__` gets through. `mutations` checks it anyway,
because a deep copy costs nothing and the field somebody adds later may not be a
scalar.

A stored snapshot can also *disagree with what the model would say now* -- refit
the same moment once later bars exist, and get a different answer. Nothing
mutated; the model simply used the future. That is repainting, and it is what
§35.3 exists to catch. `recomputations` is that check.

Both run over **every** moment in the stream rather than one, and the caller is
expected to run them over every model rather than one. Neither is true of the
test that existed before this: it fitted one model at one moment.

**A harness that walks nothing reports success**, so `replay` returns what it
examined and the caller asserts the count. That failure shape has appeared three
times in this repository now.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import dataclass

from channelflow.bars import Bar
from channelflow.channels.models import ChannelModel, ChannelSnapshot


@dataclass(frozen=True)
class Retained:
    """A snapshot as it was handed out, and a copy taken at that instant."""

    as_of_ns: int
    #: How many bars existed when this was produced. The refit uses the full
    #: series, so this records what the model was allowed to see.
    prefix_length: int
    snapshot: ChannelSnapshot
    taken: ChannelSnapshot


@dataclass(frozen=True)
class Divergence:
    """One field of one snapshot that is not what it was."""

    as_of_ns: int
    field: str
    stored: object
    now: object

    def __str__(self) -> str:
        return (
            f"at as_of_ns={self.as_of_ns}, field {self.field!r} was {self.stored!r} "
            f"and is now {self.now!r}"
        )


def replay(model: ChannelModel, bars: Sequence[Bar]) -> list[Retained]:
    """Feed the bars one at a time, keeping every snapshot and a copy of it.

    Fitting starts at the first bar where the model has its whole lookback. A
    shorter prefix is a different question -- how the model behaves on
    insufficient history -- and answering it here would mix two failures under
    one name.
    """
    retained: list[Retained] = []
    for index in range(model.lookback - 1, len(bars)):
        prefix = list(bars[: index + 1])
        snapshot = model.fit(prefix, as_of_ns=bars[index].close_time_ns)
        retained.append(
            Retained(
                as_of_ns=bars[index].close_time_ns,
                prefix_length=len(prefix),
                snapshot=snapshot,
                taken=deepcopy(snapshot),
            )
        )
    return retained


def _fields(snapshot: ChannelSnapshot) -> tuple[str, ...]:
    return tuple(type(snapshot).model_fields)


def _compare(as_of_ns: int, stored: ChannelSnapshot, other: ChannelSnapshot) -> list[Divergence]:
    """Field by field, never by object identity.

    A model that returned the same object every call would satisfy an identity
    check trivially, and that is the shape of pass this whole harness exists to
    refuse.
    """
    return [
        Divergence(
            as_of_ns=as_of_ns,
            field=field,
            stored=getattr(stored, field),
            now=getattr(other, field),
        )
        for field in _fields(stored)
        if getattr(stored, field) != getattr(other, field)
    ]


def mutations(retained: Sequence[Retained]) -> list[Divergence]:
    """Snapshots that are no longer what they were when produced."""
    found: list[Divergence] = []
    for entry in retained:
        found.extend(_compare(entry.as_of_ns, entry.taken, entry.snapshot))
    return found


def recomputations(
    build: Callable[[], ChannelModel], bars: Sequence[Bar], retained: Sequence[Retained]
) -> list[Divergence]:
    """Snapshots the model no longer agrees with, now that the future exists.

    `build` rather than a model, because a model that had carried state would
    make this a measurement of the harness. A fresh one each time asks only
    whether the answer depends on bars after `as_of_ns`.
    """
    found: list[Divergence] = []
    for entry in retained:
        refit = build().fit(list(bars), as_of_ns=entry.as_of_ns)
        found.extend(_compare(entry.as_of_ns, entry.snapshot, refit))
    return found
