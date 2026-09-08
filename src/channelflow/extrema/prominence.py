"""PRD section 13A.6's prominence filter.

# @trace: REQ-WP-019

"Noise can create many tiny extrema." Section 13A.29's first named failure mode
is tiny noisy pivots generating alert spam, and this is what stops it.

The measurement looks backward only: the excursion from the causal baseline
behind the candidate. Section 13A.6 permits SciPy-like prominence concepts for
research diagnostics and requires production logic to stay causal -- so a
prominence that measured the descent on both sides would be exactly the
centered computation ADR-022 refuses.
"""

from __future__ import annotations

from dataclasses import dataclass

BPS = 10_000.0


@dataclass(frozen=True)
class ProminenceRule:
    """PRD section 13A.6's example, with its numbers as arguments.

    prominence_atr >= 0.8 AND bars_since_previous_extremum >= 3
    """

    min_prominence_bps: float = 80.0
    min_prominence_atr: float | None = 0.8
    min_bars_between: int = 3

    def accepts(
        self,
        *,
        prominence_bps: float,
        prominence_atr: float | None,
        bars_since_previous: int | None,
    ) -> bool:
        if prominence_bps < self.min_prominence_bps:
            return False
        if (
            self.min_prominence_atr is not None
            and prominence_atr is not None
            and prominence_atr < self.min_prominence_atr
        ):
            return False
        # `None` means there is no previous extremum, which cannot be too close
        # to this one.
        if bars_since_previous is not None and bars_since_previous < self.min_bars_between:
            return False
        return True


def prominence_bps(extreme_price: float, baseline_price: float) -> float:
    """How far the extreme stands out from the causal baseline behind it."""
    if baseline_price <= 0:
        return 0.0
    return abs(extreme_price - baseline_price) / baseline_price * BPS
