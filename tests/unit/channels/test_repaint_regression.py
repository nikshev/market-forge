"""PRD §35.3's repaint regression, over every model and every moment.

The test that existed before this fitted **one** model at **one** moment,
appended future bars, refitted that moment and compared. This runs §35.3's own
procedure — feed one at a time, keep every snapshot, keep going, check them all —
across all four models.

Two hypotheses were measured while specifying this and neither survived, so
neither is claimed here: a handed-out `ChannelSnapshot` is effectively immutable
(frozen, every field a scalar or a frozen model, only `object.__setattr__` gets
through), and all four models answer identically warm and cold. This is a guard
on future code. The properties hold; nothing kept them holding.
"""

from __future__ import annotations

import pytest

from channelflow.bars import Bar
from channelflow.channels import (
    HuberChannel,
    KalmanChannel,
    QuantileChannel,
    RollingOLSChannel,
)
from channelflow.channels.models import ChannelModel, ChannelSnapshot
from channelflow.channels.repaint import (
    Retained,
    mutations,
    recomputations,
    replay,
)
from tests.unit.channels.conftest import log_linear_series

LOOKBACK = 30
BARS = 90

#: Every channel model this package ships. A fifth added without a line here
#: fails `test_every_channel_model_is_covered` by name.
MODELS: dict[str, type] = {
    "RollingOLSChannel": RollingOLSChannel,
    "HuberChannel": HuberChannel,
    "QuantileChannel": QuantileChannel,
    "KalmanChannel": KalmanChannel,
}


@pytest.fixture
def bars() -> list[Bar]:
    return log_linear_series(BARS)


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_every_channel_model_is_covered() -> None:
    """The enumeration, so a model added later is a red suite rather than a gap."""
    import channelflow.channels as package

    shipped = {
        name for name in dir(package) if name.endswith("Channel") and not name.startswith("_")
    }
    assert shipped == set(MODELS), (
        f"channel models without a repaint case: {sorted(shipped - set(MODELS))}; "
        f"named here but not shipped: {sorted(set(MODELS) - shipped)}"
    )
    assert len(MODELS) == 4


@pytest.mark.trace("REQ-NRT-REPAINT")
@pytest.mark.parametrize("name", sorted(MODELS))
def test_the_replay_examines_every_moment(name: str, bars: list[Bar]) -> None:
    """A harness that walks nothing finds no violations and reports success."""
    retained = replay(MODELS[name](lookback=LOOKBACK), bars)
    assert len(retained) == BARS - LOOKBACK + 1 == 61
    assert retained[0].prefix_length == LOOKBACK
    assert retained[-1].prefix_length == BARS
    assert [entry.as_of_ns for entry in retained] == sorted(entry.as_of_ns for entry in retained)


@pytest.mark.trace("REQ-NRT-REPAINT")
@pytest.mark.parametrize("name", sorted(MODELS))
def test_no_stored_snapshot_is_mutated(name: str, bars: list[Bar]) -> None:
    """§35.3 step 4, read literally: the stored object is still what it was."""
    retained = replay(MODELS[name](lookback=LOOKBACK), bars)
    assert mutations(retained) == []


@pytest.mark.trace("REQ-NRT-REPAINT")
@pytest.mark.parametrize("name", sorted(MODELS))
def test_no_snapshot_changes_once_the_future_exists(name: str, bars: list[Bar]) -> None:
    """§35.3's intent: refit each moment with the whole series and get the same answer."""
    model = MODELS[name]
    retained = replay(model(lookback=LOOKBACK), bars)
    found = recomputations(lambda: model(lookback=LOOKBACK), bars, retained)
    assert found == [], "\n".join(str(divergence) for divergence in found[:5])


# --- the faults, introduced on purpose ---------------------------------------


class _RepaintingChannel:
    """Answers differently once later bars exist. The failure §35.3 describes."""

    def __init__(self, *, lookback: int) -> None:
        self._inner = RollingOLSChannel(lookback=lookback)

    @property
    def lookback(self) -> int:
        return self._inner.lookback

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        snapshot = self._inner.fit(bars, as_of_ns=as_of_ns)
        # The whole point: the answer depends on how much future is available.
        after = sum(1 for bar in bars if bar.close_time_ns > as_of_ns)
        return snapshot.model_copy(update={"center_now": snapshot.center_now + after})


class _MutatingChannel:
    """Reaches into a snapshot it already handed out."""

    def __init__(self, *, lookback: int) -> None:
        self._inner = RollingOLSChannel(lookback=lookback)
        self._handed_out: list[ChannelSnapshot] = []

    @property
    def lookback(self) -> int:
        return self._inner.lookback

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        snapshot = self._inner.fit(bars, as_of_ns=as_of_ns)
        for earlier in self._handed_out:
            # Frozen models refuse assignment; this is the one route through.
            object.__setattr__(earlier, "center_now", -1.0)
        self._handed_out.append(snapshot)
        return snapshot


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_a_repainting_model_is_caught_and_named(bars: list[Bar]) -> None:
    model: ChannelModel = _RepaintingChannel(lookback=LOOKBACK)
    retained = replay(model, bars)
    assert mutations(retained) == [], "this fault is not a mutation"
    found = recomputations(lambda: _RepaintingChannel(lookback=LOOKBACK), bars, retained)
    assert found, "a model that uses the future went unnoticed"
    assert {divergence.field for divergence in found} == {"center_now"}
    assert str(found[0]).startswith("at as_of_ns=")


class _LateMutatingChannel:
    """Edits earlier snapshots, but never the very first one.

    Separate from `_MutatingChannel` on purpose. That one touches every earlier
    snapshot, so even a check that looked only at `retained[0]` would see it.
    This one leaves the first alone, so it is visible **only** to a check that
    walks the whole stream — which is the property the harness has to have.
    """

    def __init__(self, *, lookback: int) -> None:
        self._inner = RollingOLSChannel(lookback=lookback)
        self._previous: ChannelSnapshot | None = None
        self._calls = 0

    @property
    def lookback(self) -> int:
        return self._inner.lookback

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        snapshot = self._inner.fit(bars, as_of_ns=as_of_ns)
        self._calls += 1
        # From the third fit onward, so snapshot zero is never touched.
        if self._previous is not None and self._calls > 2:
            object.__setattr__(self._previous, "center_now", -1.0)
        self._previous = snapshot
        return snapshot


class _StatefulChannel:
    """Answers differently depending on how many times it has been asked.

    Nothing shipped behaves this way -- measured, all four models answer
    identically warm and cold. It exists to prove the harness builds a fresh
    model per moment rather than reusing one, because the day a model does carry
    state, a reused one would be measuring the harness.
    """

    def __init__(self, *, lookback: int) -> None:
        self._inner = RollingOLSChannel(lookback=lookback)
        self._calls = 0

    @property
    def lookback(self) -> int:
        return self._inner.lookback

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        snapshot = self._inner.fit(bars, as_of_ns=as_of_ns)
        self._calls += 1
        return snapshot.model_copy(update={"width_pct": float(self._calls)})


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_a_model_that_edits_what_it_handed_out_is_caught(bars: list[Bar]) -> None:
    retained = replay(_MutatingChannel(lookback=LOOKBACK), bars)
    found = mutations(retained)
    assert found, "a mutated snapshot went unnoticed"
    assert {divergence.field for divergence in found} == {"center_now"}
    assert all(divergence.now == -1.0 for divergence in found)
    # Every snapshot but the last was handed out before a later fit ran.
    assert len(found) == len(retained) - 1


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_a_mutation_of_only_the_latest_snapshot_is_caught_too(bars: list[Bar]) -> None:
    """A check that looked only at the first snapshot would miss this entirely."""
    retained = replay(_LateMutatingChannel(lookback=LOOKBACK), bars)
    found = mutations(retained)
    # Snapshots 1..n-2 are edited: the first is never touched, and the last was
    # never followed by another fit.
    assert len(found) == len(retained) - 2
    assert mutations(retained[:1]) == [], (
        "the first snapshot is untouched, so this fault is visible only "
        "to a check that walks the whole stream"
    )
    assert all(divergence.now == -1.0 for divergence in found)


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_each_moment_is_refitted_by_a_fresh_model(bars: list[Bar]) -> None:
    """`recomputations` takes a factory, and it has to use it every time."""
    retained = replay(RollingOLSChannel(lookback=LOOKBACK), bars)
    reused = _StatefulChannel(lookback=LOOKBACK)
    from_reused = [reused.fit(list(bars), as_of_ns=entry.as_of_ns).width_pct for entry in retained]
    assert len(set(from_reused)) == len(retained), "the fault model is not stateful"

    fresh = {
        _StatefulChannel(lookback=LOOKBACK).fit(list(bars), as_of_ns=entry.as_of_ns).width_pct
        for entry in retained
    }
    assert fresh == {1.0}, "a fresh model must answer the same way every time"

    stateful_retained = replay(_StatefulChannel(lookback=LOOKBACK), bars)
    found = recomputations(lambda: _StatefulChannel(lookback=LOOKBACK), bars, stateful_retained)
    assert {divergence.field for divergence in found} == {"width_pct"}
    assert all(divergence.now == 1.0 for divergence in found)


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_equality_is_by_value_not_by_identity(bars: list[Bar]) -> None:
    """A model returning one object for every moment must not pass trivially."""
    retained = replay(RollingOLSChannel(lookback=LOOKBACK), bars)
    first, second = retained[0], retained[1]
    assert first.snapshot is not second.snapshot
    assert first.snapshot != second.snapshot
    # And a copy, which is a different object, compares equal.
    assert first.snapshot == first.taken
    assert first.snapshot is not first.taken


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_a_snapshot_field_added_later_is_compared_too() -> None:
    """The comparison walks the model's fields rather than a list written here."""
    fields = set(ChannelSnapshot.model_fields)
    assert {"center_now", "upper_now", "lower_now", "quality"} <= fields
    assert len(fields) >= 12


@pytest.mark.trace("REQ-NRT-REPAINT")
def test_a_retained_entry_keeps_a_copy_that_is_not_the_snapshot(bars: list[Bar]) -> None:
    entry: Retained = replay(RollingOLSChannel(lookback=LOOKBACK), bars)[0]
    assert entry.snapshot is not entry.taken
    assert entry.snapshot == entry.taken
