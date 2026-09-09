"""PRD section 25.5's metrics, computed after costs.

# @trace: REQ-BT-001

PRD section 41 rule 9: **"Fees/slippage must be included in economic
evaluation."**

[[ADR-009]] deliberately kept these metrics out of backtest v1 and said what
would bring them back: section 40's outcome definitions and section 25.4's fill
models, "together with the costs section 41 rule 9 requires". All three now
exist, and this module is the last of them.

The rule is enforced rather than documented: a report cannot be built without a
cost model. ADR-009's own reasoning is why -- "a backtest that reports 62% win
rate before fees will be quoted as 62%, because the caveat does not travel with
the number". A required argument travels.

Ambiguous outcomes are excluded and counted. An ambiguous trade has no known
result: counted as a win it flatters this run, as a loss it flatters the next
configuration that happens to avoid them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median, pstdev

from channelflow.backtest.outcomes import Outcome, SignalOutcome


class CostsRequired(ValueError):
    """An economic metric was requested without fees and slippage."""


class NothingResolved(ValueError):
    """No outcome could carry a number, so there is nothing to report."""


@dataclass(frozen=True)
class CostModel:
    """What a round trip costs, in the units section 25.5 lists.

    `funding_bps` and `gas_bps` are section 25.5's "funding cost" and "DEX gas
    where applicable": a venue with neither passes zero rather than having the
    fields absent, so a comparison across venues compares the same arithmetic.
    """

    fee_bps: float
    slippage_bps: float
    funding_bps: float = 0.0
    gas_bps: float = 0.0

    def __post_init__(self) -> None:
        for name in ("fee_bps", "slippage_bps", "funding_bps", "gas_bps"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} is negative; a cost that pays the trader is not one")

    @property
    def round_trip_pct(self) -> float:
        """Entry and exit both pay the fee and the slippage."""
        return (
            2.0 * (self.fee_bps + self.slippage_bps) + self.funding_bps + self.gas_bps
        ) / 10_000.0


@dataclass(frozen=True)
class EconomicReport:
    """Section 25.5's per-setup metrics, net of costs."""

    trades: int
    excluded_ambiguous: int
    costs: CostModel
    win_rate: float
    average_return: float
    median_return: float
    expectancy_r: float
    #: `None` when nothing lost: dividing by zero losses gives infinity, which
    #: reads as a spectacular result rather than as a sample with nothing to
    #: divide by.
    profit_factor: float | None
    sharpe: float | None
    sortino: float | None
    max_drawdown: float
    average_mfe: float
    average_mae: float
    target_hit_probability: float


def economic_report(
    outcomes: Sequence[SignalOutcome], *, costs: CostModel | None, risk_per_trade: float
) -> EconomicReport:
    """Section 25.5's metrics over resolved outcomes, after `costs`."""
    if costs is None:
        raise CostsRequired(
            "PRD section 41 rule 9 requires fees and slippage in any economic "
            "evaluation; a gross figure is quoted as the figure, because the caveat "
            "does not travel with the number (ADR-009)"
        )
    if risk_per_trade <= 0.0:
        raise ValueError("risk per trade must be positive; expectancy in R divides by it")

    resolved = [o for o in outcomes if o.resolved]
    excluded = len(outcomes) - len(resolved)
    if not resolved:
        raise NothingResolved(
            f"none of {len(outcomes)} outcome(s) resolved; a profit factor over nothing "
            "is not zero, and a win rate over nothing is not 0%"
        )

    charge = costs.round_trip_pct
    returns = [o.return_h - charge for o in resolved]
    wins = [r for r in returns if r > 0.0]
    losses = [r for r in returns if r < 0.0]

    average = sum(returns) / len(returns)
    spread = pstdev(returns) if len(returns) > 1 else 0.0
    downside = pstdev([min(r, 0.0) for r in returns]) if len(returns) > 1 else 0.0

    return EconomicReport(
        trades=len(resolved),
        excluded_ambiguous=excluded,
        costs=costs,
        win_rate=len(wins) / len(returns),
        average_return=average,
        median_return=median(returns),
        # Section 25.5's "expectancy in R": the net average in units of what was
        # risked, which is what makes two setups comparable when one risks 2%
        # and the other half a percent.
        expectancy_r=average / risk_per_trade,
        profit_factor=(sum(wins) / abs(sum(losses))) if losses else None,
        sharpe=(average / spread) if spread > 0.0 else None,
        sortino=(average / downside) if downside > 0.0 else None,
        max_drawdown=_max_drawdown(returns),
        average_mfe=sum(o.mfe_pct for o in resolved) / len(resolved),
        average_mae=sum(o.mae_pct for o in resolved) / len(resolved),
        target_hit_probability=sum(1 for o in resolved if o.outcome is Outcome.TARGET)
        / len(resolved),
    )


def _max_drawdown(returns: list[float]) -> float:
    """The worst fall from a running peak, over the equity path.

    Of the path, not of one trade: three losses in a row draw down more than the
    worst of them, and a maximum drawdown equal to the worst single trade is a
    different statistic under the same name.
    """
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for r in returns:
        equity += r
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return worst
