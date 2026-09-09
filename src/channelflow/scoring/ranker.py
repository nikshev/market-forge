"""PRD section 43's alert ranker and section 22.3's threshold.

# @trace: REQ-SCORE-001

    rank_score = setup_score * data_quality * liquidity_factor * novelty_factor

    "- `data_quality` penalizes stale/missing sources;
     - `liquidity_factor` prevents noisy illiquid assets dominating;
     - `novelty_factor` reduces repeated correlated alerts."

All three are penalties, so all three are bounded to `[0, 1]`. Above 1 any of
them becomes a bonus, and a stale, illiquid, repeated alert could then outrank a
fresh one -- the exact inversion the section exists to prevent.

Section 22.3 makes the alert threshold "configurable per symbol/timeframe/setup"
and calls `score >= 75` a "default research value only". The value arrives with
that label attached, so nobody downstream reads the PRD's placeholder as a
validated production threshold ([[ADR-016]] deferred this here).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

#: Section 22.3's default. A research value, and it says so where it is used.
DEFAULT_ALERT_THRESHOLD = 75.0

#: Symbol, timeframe, setup type -- `None` in a position means "any".
OverrideKey = tuple[str | None, int | None, str | None]


class FactorOutOfRange(ValueError):
    """A ranking factor was outside `[0, 1]`."""


@dataclass(frozen=True)
class RankInput:
    """One candidate for the ranked list."""

    key: str
    setup_score: float
    data_quality: float = 1.0
    liquidity_factor: float = 1.0
    novelty_factor: float = 1.0


@dataclass(frozen=True)
class Ranked:
    """A candidate and the rank score it earned."""

    key: str
    rank_score: float
    setup_score: float
    data_quality: float
    liquidity_factor: float
    novelty_factor: float


@dataclass(frozen=True)
class ResolvedThreshold:
    """A threshold, and whether it is anybody's decision or the PRD's default."""

    value: float
    is_research_default: bool


def rank_score(
    *,
    setup_score: float,
    data_quality: float,
    liquidity_factor: float,
    novelty_factor: float,
) -> float:
    """Section 43's product."""
    for name, value in (
        ("data_quality", data_quality),
        ("liquidity_factor", liquidity_factor),
        ("novelty_factor", novelty_factor),
    ):
        if not 0.0 <= value <= 1.0:
            raise FactorOutOfRange(
                f"{name} is {value}, outside [0, 1]; section 43's factors are penalties, "
                "and one above 1 would let a stale or illiquid candidate outrank a fresh one"
            )
    if setup_score < 0.0:
        raise FactorOutOfRange(f"setup_score is {setup_score}; a score below zero is not a score")
    return setup_score * data_quality * liquidity_factor * novelty_factor


def rank(candidates: Sequence[RankInput]) -> tuple[Ranked, ...]:
    """Highest rank score first, ties broken by key.

    The tie-break is what makes the list the same list twice. Ordered by rank
    score alone, two equal candidates would swap places between refreshes
    depending on how the input happened to be assembled.
    """
    scored = [
        Ranked(
            key=c.key,
            rank_score=rank_score(
                setup_score=c.setup_score,
                data_quality=c.data_quality,
                liquidity_factor=c.liquidity_factor,
                novelty_factor=c.novelty_factor,
            ),
            setup_score=c.setup_score,
            data_quality=c.data_quality,
            liquidity_factor=c.liquidity_factor,
            novelty_factor=c.novelty_factor,
        )
        for c in candidates
    ]
    return tuple(sorted(scored, key=lambda r: (-r.rank_score, r.key)))


@dataclass(frozen=True)
class AlertThresholds:
    """Section 22.3's configurable threshold, resolved most-specific-first."""

    default: float = DEFAULT_ALERT_THRESHOLD
    overrides: dict[OverrideKey, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value in (self.default, *self.overrides.values()):
            if not 0.0 <= value <= 100.0:
                raise ValueError(
                    f"threshold {value} is outside the score's own range [0, 100]; above "
                    "100 it can never be met and below zero it always is, and either "
                    "turns the alert gate into a constant"
                )

    def resolve(self, *, symbol: str, timeframe_ns: int, setup: str) -> ResolvedThreshold:
        """The most specific override, or the PRD's default.

        Specificity is fixed here rather than discovered from the keys: with
        overrides at more than one level, picking the first match found would
        make the answer depend on dictionary order.
        """
        for key in (
            (symbol, timeframe_ns, setup),
            (symbol, timeframe_ns, None),
            (symbol, None, setup),
            (symbol, None, None),
            (None, timeframe_ns, setup),
            (None, timeframe_ns, None),
            (None, None, setup),
        ):
            if key in self.overrides:
                return ResolvedThreshold(value=self.overrides[key], is_research_default=False)
        return ResolvedThreshold(
            value=self.default, is_research_default=self.default == DEFAULT_ALERT_THRESHOLD
        )
