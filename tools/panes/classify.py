# @trace: REQ-WP-097
"""The three states a lower pane can be in, decided from the API's own answers.

* `data`: at least one point in the loaded range carries the pane's feature.
* `absent`: no point does, and the system says why -- a refusal reason the consensus read stored,
  a window the liquidation stream watched and in which nothing was liquidated, a pane whose source
  is not part of this deployment.
* `no-producer`: no point does and nothing says why. This is the state REQ-WP-097 exists to
  remove: a pane that is empty because the thing that would fill it is not running looks, on the
  page, exactly like a quiet market.

The reasons come from the system's answers, never from a list of excuses kept here. The one
exception is stated: the DEX panes have no source in this deployment (no ingest, no compose
service), so their absence is reported as exactly that -- a true reason, named, and the only place
this module knows a fact the API does not tell it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

DATA = "data"
ABSENT = "absent"
NO_PRODUCER = "no-producer"

#: Feature panes whose source this deployment does not have. Named here, not discovered: the API
#: cannot say "I have no DEX ingest", and saying nothing would report them as NO PRODUCER for ever.
NO_SOURCE_IN_DEPLOYMENT: Mapping[str, str] = {
    "dex_swap_imbalance": "no DEX source: this deployment runs no DEX ingest",
    "dex_active_liquidity": "no DEX source: this deployment runs no DEX ingest",
}

#: The feature rows that prove a liquidation stream was listening for a window: a covered window
#: writes both USD sums (zero is a reading there), an uncovered one writes none.
LIQUIDATION_COVERAGE = "liquidation_long_usd_5m"


@dataclass(frozen=True)
class PaneState:
    state: str
    reason: str = ""

    def render(self) -> str:
        if self.state == ABSENT:
            return f"absent: {self.reason}"
        return self.state if not self.reason else f"{self.state}: {self.reason}"


@dataclass(frozen=True)
class Evidence:
    """What the API answered for one market and timeframe."""

    #: Feature name -> number of points in the loaded range that carry it.
    feature_counts: Mapping[str, int]
    #: Bars loaded for the range (the Volume pane reads these, not a feature).
    bars: int
    #: The consensus read's answer for this market: refusal reasons, or `None` if the read itself
    #: failed (a 404 for a market with no consensus rows).
    consensus_reasons: Sequence[str] | None
    consensus_error: str | None = None


def count_features(points: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """How many points carry each feature, counting only real numbers."""
    counts: dict[str, int] = {}
    for point in points:
        for name, value in (point.get("values") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                counts[name] = counts.get(name, 0) + 1
    return counts


def classify(feature: str, evidence: Evidence) -> PaneState:
    """The state of one pane, from the evidence about one market and timeframe."""
    if feature == "volume":
        return PaneState(DATA) if evidence.bars > 0 else PaneState(NO_PRODUCER, "no bars in range")
    if evidence.feature_counts.get(feature, 0) > 0:
        return PaneState(DATA)

    if feature in NO_SOURCE_IN_DEPLOYMENT:
        return PaneState(ABSENT, NO_SOURCE_IN_DEPLOYMENT[feature])

    if feature == "venue_basis_bps":
        if evidence.consensus_reasons:
            return PaneState(ABSENT, "; ".join(sorted(set(evidence.consensus_reasons))))
        if evidence.consensus_error:
            return PaneState(
                NO_PRODUCER, f"the consensus read answered: {evidence.consensus_error}"
            )
        return PaneState(NO_PRODUCER, "consensus rows exist and no venue basis was derived")

    if feature == "liquidation_imbalance_5m":
        if evidence.feature_counts.get(LIQUIDATION_COVERAGE, 0) > 0:
            return PaneState(
                ABSENT,
                "no liquidation in the range, and the stream was listening "
                f"({evidence.feature_counts[LIQUIDATION_COVERAGE]} covered windows)",
            )
        return PaneState(
            NO_PRODUCER, "no covered window: the liquidation stream wrote no heartbeat"
        )

    return PaneState(NO_PRODUCER, "nothing stored for this feature")
