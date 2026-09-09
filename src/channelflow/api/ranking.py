"""Ordering the market list by PRD section 43's rank score.

# @trace: REQ-US-001

REQ-US-001 asks for the list "sorted by setup score, so that I can quickly find
the most interesting situations". Section 43 is what turns a setup score into an
order:

    rank_score = setup_score * data_quality * liquidity_factor * novelty_factor

Here rather than in the handler for the same reason the refit lives in
`channels.py`: the endpoints read and shape, and anything with a rule in it
belongs somewhere a test can reach without a client.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.api.repositories import Market, Repository, ScoredSetup
from channelflow.scoring import RankInput, rank


@dataclass(frozen=True)
class RankedMarket:
    """A market in its place, with the numbers that put it there."""

    market: Market
    scored: ScoredSetup | None
    rank_score: float | None


def rank_markets(markets: list[Market], *, repository: Repository) -> tuple[RankedMarket, ...]:
    """Scored markets by rank score, then the rest by name.

    An unscored market is not a market that scored zero, so it is not ranked at
    zero: that would place it among the worst setups and say it had been
    examined and found weak. It sorts after every scored one instead, and its
    scores travel as nulls.

    The tail is ordered by name rather than left as the repository held it, so
    the whole list is a list rather than an order that happens to be stable
    today.
    """
    scores = {_key(m): repository.setup_score(venue=m.venue, symbol=m.symbol) for m in markets}
    ranked = rank(
        [
            RankInput(
                key=_key(m),
                setup_score=scored.score.final,
                data_quality=scored.score.data_quality,
                liquidity_factor=scored.liquidity_factor,
                novelty_factor=scored.novelty_factor,
            )
            for m in markets
            if (scored := scores[_key(m)]) is not None
        ]
    )
    position = {r.key: index for index, r in enumerate(ranked)}
    rank_scores = {r.key: r.rank_score for r in ranked}
    unscored_place = len(ranked)

    return tuple(
        RankedMarket(
            market=m,
            scored=scores[_key(m)],
            rank_score=rank_scores.get(_key(m)),
        )
        for m in sorted(markets, key=lambda m: (position.get(_key(m), unscored_place), _key(m)))
    )


def _key(market: Market) -> str:
    return f"{market.venue}:{market.symbol}"
