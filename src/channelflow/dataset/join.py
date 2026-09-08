"""PRD section 24.2's training join.

# @trace: REQ-WP-017
# @trace: REQ-BIAS-004
# @trace: REQ-BIAS-007
# @trace: REQ-BIAS-008

    features(t) ---------------> model input
          |
          | no feature after t
          v
    label(t, t+H) -------------> target only

Five ways a row can fail to be built, and each is a named reason rather than a
`None`. A caller that gets `None` five times cannot tell a missing snapshot
from a leaking one, and the difference is the difference between "we have no
data here" and "our dataset is contaminated".

The universe lives here too (PRD section 42): it decides which rows may exist
at all, which makes it a filter on the join rather than a thing of its own.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

from channelflow.dataset.models import FeatureSnapshot, Label, Row


class DropReason(StrEnum):
    """Why a row was not built. Counted separately, always."""

    NO_SNAPSHOT = "no_snapshot_at_or_before_t"
    UNFINALIZED_BAR = "feature_from_a_bar_not_yet_closed"
    NOT_IN_UNIVERSE = "entity_not_in_the_universe_at_t"
    AMBIGUOUS_SNAPSHOT = "two_snapshots_indistinguishable_at_t"
    NO_LABEL = "label_horizon_extends_past_the_data"


@dataclass(frozen=True)
class Listing:
    """PRD section 42: when a symbol existed, and when it stopped."""

    entity: str
    listed_ns: int
    delisted_ns: int | None = None

    def live_at(self, at_ns: int) -> bool:
        if at_ns < self.listed_ns:
            return False
        return self.delisted_ns is None or at_ns < self.delisted_ns


@dataclass
class PointInTimeUniverse:
    """Which symbols existed and were eligible at an instant.

    PRD section 41 rules 7 and 8: no survivor-only universe, and no using
    today's top-volume list for a historical backtest. Both are the same
    mistake -- asking what is tradeable now and pretending it was tradeable
    then -- and both are avoided by never having a "now" to ask about.
    """

    listings: list[Listing] = field(default_factory=list)
    #: Trailing volume per entity, as observed. Eligibility reads only entries
    #: at or before the instant asked about.
    volume_observations: dict[str, list[tuple[int, float]]] = field(default_factory=dict)
    min_trailing_volume: float = 0.0

    def at(self, at_ns: int) -> set[str]:
        eligible: set[str] = set()
        for listing in self.listings:
            if not listing.live_at(at_ns):
                continue
            if self.min_trailing_volume > 0.0:
                observed = [
                    volume
                    for time_ns, volume in self.volume_observations.get(listing.entity, [])
                    if time_ns <= at_ns
                ]
                if not observed or observed[-1] < self.min_trailing_volume:
                    continue
            eligible.add(listing.entity)
        return eligible


@dataclass(frozen=True)
class BuildReport:
    """What was built, and everything that was not.

    The counts are not diagnostics. "No rows" and "every row dropped because
    the universe was empty" are different results, and a build that returned
    an empty list for both would be unreadable.
    """

    rows: tuple[Row, ...]
    dropped: dict[str, int]

    @property
    def built(self) -> int:
        return len(self.rows)

    @property
    def considered(self) -> int:
        return self.built + sum(self.dropped.values())


def as_of_snapshot(
    snapshots: list[FeatureSnapshot], *, entity: str, feature_name: str, at_ns: int
) -> FeatureSnapshot | None:
    """The most recent snapshot at or before `at_ns` -- never a later one.

    Ties on `as_of_ns` are broken by `source_max_event_ns`; a tie on both is
    ambiguous and refused by the caller, because nothing in the data can break
    it and picking arbitrarily would make the dataset depend on list order.
    """
    eligible = [
        s
        for s in snapshots
        if s.entity == entity and s.feature_name == feature_name and s.as_of_ns <= at_ns
    ]
    if not eligible:
        return None
    latest = max(eligible, key=lambda s: (s.as_of_ns, s.source_max_event_ns))
    contenders = [
        s
        for s in eligible
        if s.as_of_ns == latest.as_of_ns and s.source_max_event_ns == latest.source_max_event_ns
    ]
    if len(contenders) > 1:
        raise AmbiguousSnapshot(
            f"{len(contenders)} snapshots of {feature_name!r} for {entity!r} are "
            f"indistinguishable at {at_ns}: same as_of_time and same "
            "source_max_event_time. Nothing in the data breaks the tie."
        )
    return latest


class AmbiguousSnapshot(ValueError):
    """Two snapshots that the data cannot choose between."""


def build_rows(
    *,
    entity: str,
    as_of_times: list[int],
    snapshots: list[FeatureSnapshot],
    feature_names: list[str],
    labels: dict[int, Label],
    universe: PointInTimeUniverse | None = None,
) -> BuildReport:
    """One row per instant, or a counted reason there is none."""
    rows: list[Row] = []
    dropped: Counter[str] = Counter()

    for at_ns in sorted(as_of_times):
        if universe is not None and entity not in universe.at(at_ns):
            dropped[DropReason.NOT_IN_UNIVERSE] += 1
            continue

        label = labels.get(at_ns)
        if label is None:
            dropped[DropReason.NO_LABEL] += 1
            continue

        values: dict[str, float] = {}
        source_max = 0
        failed: str | None = None
        for name in feature_names:
            try:
                snapshot = as_of_snapshot(snapshots, entity=entity, feature_name=name, at_ns=at_ns)
            except AmbiguousSnapshot:
                failed = DropReason.AMBIGUOUS_SNAPSHOT
                break
            if snapshot is None:
                # Never forward-filled from a later value: that is the leak
                # this whole module exists to prevent, and it would be
                # invisible in the row.
                failed = DropReason.NO_SNAPSHOT
                break
            if not snapshot.from_finalized_bars:
                # PRD section 41 rule 4, generalized past "daily".
                failed = DropReason.UNFINALIZED_BAR
                break
            values[name] = snapshot.value
            source_max = max(source_max, snapshot.source_max_event_ns)

        if failed is not None:
            dropped[failed] += 1
            continue

        rows.append(
            Row(
                entity=entity,
                as_of_ns=at_ns,
                features=values,
                source_max_event_ns=source_max,
                label=label,
            )
        )

    return BuildReport(rows=tuple(rows), dropped=dict(dropped))
