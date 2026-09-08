"""PRD section 18.17's multi-provider strategy.

# @trace: REQ-WP-014

    "RPC is infrastructure, not a source of unquestioned truth."

The protocol is defined here and no implementation ships. That is the same
boundary ADR-012 drew for the order book's transport and ADR-018 for the
alerter's: the thing that touches the outside world is supplied, so the code
that makes decisions can be tested without it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class NoHealthyProvider(RuntimeError):
    """Every provider is in cooldown or unhealthy.

    Refusing rather than returning the least-bad one: data from a provider
    known to be failing looks exactly like data from a working one, and the
    consumer has no way to tell.
    """


class ChainDataProvider(Protocol):
    """PRD section 18.17's interface."""

    name: str

    def get_block(self, number: int) -> dict[str, Any]: ...

    def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]: ...

    def eth_call(self, *, to: str, data: str, block: int) -> str: ...


@dataclass
class ProviderHealth:
    """What a provider has been doing *lately*.

    Counts rather than a single score, because the three failure modes need
    different responses: latency means route elsewhere, errors mean cool down,
    gaps mean the data is incomplete and a backfill is owed.

    All three are computed over a rolling window rather than the provider's
    lifetime. A lifetime rate on a long-running process is meaningless -- one
    bad hour poisons a week, and a provider that recovered can never be routed
    to again. Found by a test that expected a cooldown to expire and watched
    the provider stay unhealthy for ever.
    """

    name: str
    #: How many recent calls the rates are computed over.
    window: int = 50
    cooldown_until_ns: int | None = None
    #: (latency_ms, error, gap) per call, most recent last, trimmed to `window`.
    _recent: list[tuple[float, bool, bool]] = field(default_factory=list)
    #: Lifetime totals, kept because they are what an operator asks about.
    calls: int = 0
    errors: int = 0
    gaps: int = 0

    @property
    def error_rate(self) -> float:
        return self._rate(1)

    @property
    def gap_rate(self) -> float:
        return self._rate(2)

    @property
    def mean_latency_ms(self) -> float:
        if not self._recent:
            return 0.0
        return sum(entry[0] for entry in self._recent) / len(self._recent)

    def _rate(self, index: int) -> float:
        if not self._recent:
            return 0.0
        return sum(1 for entry in self._recent if entry[index]) / len(self._recent)

    def record(self, *, latency_ms: float, error: bool = False, gap: bool = False) -> None:
        self.calls += 1
        if error:
            self.errors += 1
        if gap:
            self.gaps += 1
        self._recent.append((latency_ms, error, gap))
        del self._recent[: max(0, len(self._recent) - self.window)]

    def healthy_at(self, at_ns: int, *, max_error_rate: float) -> bool:
        if self.cooldown_until_ns is not None and at_ns < self.cooldown_until_ns:
            return False
        return self.error_rate <= max_error_rate


@dataclass
class ProviderPool:
    """Routing, health and cooldown. No I/O; the providers are the caller's."""

    #: PRD section 18.17's "provider cooldown on rate-limit/error storms".
    max_error_rate: float = 0.2
    cooldown_ns: int = 60 * 1_000_000_000
    health: dict[str, ProviderHealth] = field(default_factory=dict)

    def observe(
        self, name: str, *, latency_ms: float, at_ns: int, error: bool = False, gap: bool = False
    ) -> ProviderHealth:
        state = self.health.setdefault(name, ProviderHealth(name=name))
        state.record(latency_ms=latency_ms, error=error, gap=gap)
        if error and state.error_rate > self.max_error_rate:
            state.cooldown_until_ns = at_ns + self.cooldown_ns
        return state

    def choose(self, at_ns: int) -> ProviderHealth:
        """The healthiest provider not in cooldown, by mean latency."""
        candidates = [
            h
            for h in self.health.values()
            if h.healthy_at(at_ns, max_error_rate=self.max_error_rate)
        ]
        if not candidates:
            raise NoHealthyProvider(
                f"no provider is healthy at {at_ns}; returning a failing one would "
                "produce data indistinguishable from good data"
            )
        return min(candidates, key=lambda h: h.mean_latency_ms)


@dataclass(frozen=True)
class Disagreement:
    """PRD section 18.17's "sampled cross-provider consistency checks".

    Reported, never resolved. Two providers disagreeing about a block hash is
    a fact about the infrastructure; picking one and moving on would hide the
    only signal that something is wrong.
    """

    block_number: int
    answers: dict[str, str]

    @property
    def distinct(self) -> int:
        return len(set(self.answers.values()))


def compare_providers(block_number: int, answers: dict[str, str]) -> Disagreement | None:
    if len(set(answers.values())) <= 1:
        return None
    return Disagreement(block_number=block_number, answers=dict(answers))
