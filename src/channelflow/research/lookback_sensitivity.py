"""EXP-002: how much the lookback matters, and how to choose one.

# @trace: REQ-EXP-002

    Lookbacks: 40; 60; 80; 100; 150; 200 bars.

    "Do not select solely on maximum PnL; evaluate stability plateau."

That second line is the experiment. Sweeping six lookbacks is arithmetic; the
rule is about what may be done with the answer, and it cannot be kept by saying
so in a docstring -- a report that names the best expectancy and nothing else
*is* selection by maximum PnL, whatever surrounds it.

So the recommendation comes from the plateau, the peak is reported beside it so
the two can be compared, and when there is no plateau there is no
recommendation. The peak is never a fallback. A peak is where the noise happened
to help; a plateau is where the choice does not matter much, which is the only
kind of choice that survives new data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.backtest import CostModel, CostsRequired
from channelflow.bars import Bar
from channelflow.channels import RollingOLSChannel
from channelflow.research.channel_comparison import (
    DEFAULT_HORIZON,
    DEFAULT_TEST_FRACTION,
    SeriesTooShort,
    compare_channel_models,
)

#: EXP-002's own list, in its order. Adjacency is by position here, not by
#: numeric distance: 150 and 200 are neighbours in this sweep though fifty bars
#: apart, because that is the resolution the experiment chose.
LOOKBACKS: tuple[int, ...] = (40, 60, 80, 100, 150, 200)

#: How close two adjacent lookbacks must be, in R, to count as the same answer.
#: A research default: it sets what "does not matter much" means, and PRD
#: section 13.11's warning about research defaults applies to it too.
DEFAULT_TOLERANCE = 0.10


@dataclass(frozen=True)
class SweepEntry:
    """One lookback's result, or why it has none."""

    lookback: int
    expectancy_r: float | None = None
    trades: int = 0
    reason: str = ""


@dataclass(frozen=True)
class Plateau:
    """A run of adjacent lookbacks that agree, and the tolerance that says so."""

    lookbacks: tuple[int, ...]
    tolerance: float
    best_expectancy_r: float

    @property
    def centre(self) -> int:
        """The middle of the run -- the furthest point from either edge."""
        return self.lookbacks[len(self.lookbacks) // 2]


@dataclass(frozen=True)
class Recommendation:
    """What to use, what the plateau was, and where the peak sat."""

    lookback: int | None
    plateau: Plateau | None
    peak_lookback: int | None
    peak_expectancy_r: float | None
    reason: str = ""


@dataclass(frozen=True)
class SweepReport:
    """Every lookback, and the recommendation over them."""

    entries: tuple[SweepEntry, ...]
    recommendation: Recommendation
    tolerance: float
    costs: CostModel


def sweep_lookbacks(
    bars: list[Bar],
    *,
    costs: CostModel | None,
    lookbacks: Sequence[int] = LOOKBACKS,
    tolerance: float = DEFAULT_TOLERANCE,
    horizon: int = DEFAULT_HORIZON,
    test_fraction: float = DEFAULT_TEST_FRACTION,
) -> SweepReport:
    """Measure every lookback the same way, then choose by plateau."""
    if costs is None:
        raise CostsRequired(
            "expectancy is an economic metric, and PRD section 41 rule 9 governs it "
            "wherever it is computed"
        )

    entries: list[SweepEntry] = []
    for lookback in lookbacks:
        model = RollingOLSChannel(lookback=lookback)
        try:
            report = compare_channel_models(
                bars,
                costs=costs,
                models={f"lookback_{lookback}": model},
                horizon=horizon,
                test_fraction=test_fraction,
            )
        except SeriesTooShort as exc:
            # A fact about the series, not about the lookback -- and it must not
            # cost the reader the lookbacks that did fit.
            entries.append(SweepEntry(lookback=lookback, reason=str(exc)))
            continue
        entry = report.entries[f"lookback_{lookback}"]
        entries.append(
            SweepEntry(
                lookback=lookback,
                expectancy_r=entry.expectancy_r,
                trades=entry.trades,
                reason=entry.reason or entry.expectancy_note,
            )
        )

    return SweepReport(
        entries=tuple(entries),
        recommendation=recommend(entries, tolerance=tolerance),
        tolerance=tolerance,
        costs=costs,
    )


def find_plateau(entries: Sequence[SweepEntry], *, tolerance: float) -> Plateau | None:
    """The widest run of adjacent lookbacks whose values agree within `tolerance`.

    An absent value breaks a run rather than being skipped: joining the two sides
    across a lookback nobody could measure produces a plateau that exists only in
    the report.

    A run of one is not a plateau. It is the peak under another name, and
    recommending it is what EXP-002 forbids.

    Ties between equally wide runs go to the one with the highest expectancy in
    it. Taking whichever the scan reached first would make the recommendation
    depend on iteration order.
    """
    runs: list[list[SweepEntry]] = []
    current: list[SweepEntry] = []

    for item in entries:
        if item.expectancy_r is None:
            runs.append(current)
            current = []
            continue
        if current and abs(item.expectancy_r - current[-1].expectancy_r) > tolerance:  # type: ignore[operator]
            runs.append(current)
            current = []
        current.append(item)
    runs.append(current)

    qualifying = [run for run in runs if len(run) >= 2]
    if not qualifying:
        return None

    best = max(
        qualifying,
        key=lambda run: (len(run), max(e.expectancy_r or 0.0 for e in run)),
    )
    return Plateau(
        lookbacks=tuple(e.lookback for e in best),
        tolerance=tolerance,
        best_expectancy_r=max(e.expectancy_r or 0.0 for e in best),
    )


def recommend(entries: Sequence[SweepEntry], *, tolerance: float) -> Recommendation:
    """The plateau's centre, with the peak named beside it.

    Never the peak, and never the peak as a fallback: "do not select solely on
    maximum PnL" is a rule about the selection, and a default that reaches for
    the peak when no plateau exists is that rule broken exactly where it
    matters.
    """
    measured = [e for e in entries if e.expectancy_r is not None]
    peak = max(measured, key=lambda e: (e.expectancy_r or 0.0, e.lookback), default=None)
    plateau = find_plateau(entries, tolerance=tolerance)

    if plateau is None:
        return Recommendation(
            lookback=None,
            plateau=None,
            peak_lookback=peak.lookback if peak else None,
            peak_expectancy_r=peak.expectancy_r if peak else None,
            reason=(
                "no plateau: no two adjacent lookbacks agreed within the tolerance, so "
                "there is no region where the choice does not matter. The peak is "
                "reported but not recommended (EXP-002)"
            ),
        )

    return Recommendation(
        lookback=plateau.centre,
        plateau=plateau,
        peak_lookback=peak.lookback if peak else None,
        peak_expectancy_r=peak.expectancy_r if peak else None,
        reason=f"centre of the widest plateau, {len(plateau.lookbacks)} lookbacks wide",
    )
