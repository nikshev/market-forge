"""PRD §35.4's future-leak test, as something that can be enumerated.

# @trace: REQ-NRT-LEAK

    For every feature:
      1. Run on truncated dataset through `t`.
      2. Run on full dataset but ask for feature at `t`.
      3. Values must match exactly within numeric tolerance.

**What this module is not.** It is not a harness that computes features. The 55
registered features share no interface -- some take events with a window, some a
book service, some scalars, some a stateful tracker -- and a `FeatureSpec` is
metadata plus the name of the test that pins its arithmetic. It carries no
callable. So each case supplies both of its own runs, and what lives here is the
comparison and the bookkeeping that makes "for every feature" mean something.

**`uncovered` is the point.** A suite that checks the features somebody
remembered grows a hole every time one is added. This does the set difference
against the registry, so the gap is a value a test can assert on rather than an
absence nobody can see.

**A feature is refused, never skipped.** A skip reports green, and green is
precisely what a leak needs in order to survive. A `Refusal` costs a written
reason, which is the price of saying a feature cannot be checked this way.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from math import isclose, isnan

#: How far two floating-point answers may differ and still be the same answer.
#:
#: Relative, not absolute: these features' units run from a ratio to a notional,
#: and one absolute epsilon cannot mean anything across both. The value is the
#: neighbourhood of double-precision accumulation over a few thousand
#: operations, chosen here rather than raised later -- a tolerance widened until
#: the suite passes is the failure, renamed.
RELATIVE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class TruncationCase:
    """One feature, one moment, and the two runs §35.4 asks to compare.

    Both sides are callables rather than values so that nothing is computed
    until the comparison runs -- a case that raises should raise inside the test
    that owns it, naming the feature, rather than at import.
    """

    feature: str
    at_ns: int
    #: Computed at `t` from input truncated at `t`.
    truncated: Callable[[], object]
    #: Computed at `t` from the whole input.
    full: Callable[[], object]


@dataclass(frozen=True)
class Refusal:
    """A feature that cannot be checked this way, and why.

    The reason is required. "Cannot be checked" without one is indistinguishable
    from "nobody got to it", and the two deserve different treatment.
    """

    feature: str
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError(
                f"refusing {self.feature} needs a reason; a refusal without one is a "
                "skip wearing a different name"
            )


@dataclass(frozen=True)
class Divergence:
    """A feature that answered differently once the future was available."""

    feature: str
    at_ns: int
    truncated: object
    full: object

    def __str__(self) -> str:
        return (
            f"{self.feature} at {self.at_ns}: truncated gave {self.truncated!r}, "
            f"full gave {self.full!r} -- the value depends on data after t"
        )


def uncovered(
    registry: Mapping[str, object],
    cases: Iterable[TruncationCase],
    refusals: Iterable[Refusal],
) -> frozenset[str]:
    """Registered features with neither a case nor a refusal.

    Raises on a case or refusal naming a feature the registry does not hold: a
    misspelled name would otherwise read as coverage, which is the one direction
    this must never fail in.
    """
    named = [case.feature for case in cases] + [refusal.feature for refusal in refusals]
    for name in named:
        if name not in registry:
            raise KeyError(
                f"{name} is not a registered feature; a case naming a feature that "
                "does not exist covers nothing"
            )
    return frozenset(registry) - frozenset(named)


def _same(left: object, right: object) -> bool:
    """Exact everywhere except floating point, which gets the stated tolerance."""
    if isinstance(left, float) and isinstance(right, float):
        if isnan(left) and isnan(right):
            return True
        return isclose(left, right, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0)
    return bool(left == right) and type(left) is type(right)


def divergence(case: TruncationCase) -> Divergence | None:
    """`None` when the two runs agree, and what differed when they do not."""
    truncated = case.truncated()
    full = case.full()
    if _same(truncated, full):
        return None
    return Divergence(feature=case.feature, at_ns=case.at_ns, truncated=truncated, full=full)
