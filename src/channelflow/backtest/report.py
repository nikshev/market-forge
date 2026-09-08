"""What a replay produced.

# @trace: REQ-WP-010

Signal-quality metrics only. ADR-009: PRD section 25.5 lists twenty metrics, but
almost all need an outcome definition (section 40) and a fill model (section
25.4), and section 41 rule 9 requires fees and slippage in any economic
evaluation. A gross win rate would be quoted as the win rate, because a caveat
does not travel with the number.

The gap between this report and section 25.5's list is the visible measure of
what is still unbuilt. Filling it with computable-but-meaningless figures would
hide that.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from channelflow.signals import CandidateState, Transition

#: Field names this report must never carry, enforced by a test. ADR-009 is a
#: decision someone could forget; this makes forgetting it fail.
FORBIDDEN_ECONOMIC_FIELDS = frozenset(
    {
        "win_rate",
        "average_return",
        "median_return",
        "expectancy",
        "expectancy_r",
        "profit_factor",
        "sharpe",
        "sortino",
        "max_drawdown",
        "pnl",
        "fees",
        "slippage",
    }
)


class BacktestReport(BaseModel):
    """One replay pass, and the configuration that produced it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bars_replayed: int = Field(ge=0)
    #: Bars where no channel could be fitted. "No setups found" and "we could
    #: never look" are different results wearing the same zero.
    bars_skipped_no_channel: int = Field(ge=0)
    first_bar_close_ns: int = Field(ge=0)
    last_bar_close_ns: int = Field(ge=0)

    candidates_opened: int = Field(ge=0)
    by_direction: dict[str, int]
    by_boundary: dict[str, int]
    confirmed: int = Field(ge=0)
    terminal_reasons: dict[str, int]

    transitions: tuple[Transition, ...]

    #: PRD section 13.11 calls the zone bounds research defaults. Two runs whose
    #: reports cannot be told apart are two runs whose difference cannot be
    #: attributed to anything.
    configuration: dict[str, str]

    @property
    def confirmation_rate(self) -> float:
        return self.confirmed / self.candidates_opened if self.candidates_opened else 0.0

    @property
    def states_reached(self) -> dict[CandidateState, int]:
        counts: dict[CandidateState, int] = {}
        for transition in self.transitions:
            counts[transition.to_state] = counts.get(transition.to_state, 0) + 1
        return counts
