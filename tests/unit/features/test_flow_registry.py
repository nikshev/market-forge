"""The registry side of REQ-WP-088: six documented features; which venues have sequential ids."""

from __future__ import annotations

import pytest

from channelflow.connectors.venue import VENUE_REGISTRY
from channelflow.features import REGISTRY
from channelflow.features.flow_bars import FLOW_FEATURES


@pytest.mark.trace("REQ-WP-088")
@pytest.mark.parametrize("name", FLOW_FEATURES)
def test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated(name: str) -> None:
    """Principle VI: documented, and a base-unit CVD must not pass for the PRD's notional one."""
    spec = REGISTRY[name]

    assert spec.formula and spec.unit
    if name != "cvd_run":  # a count of breaks, not a base-unit quantity
        assert "base" in spec.unit.lower() or spec.unit == "ratio"
        assert "ADR-068" in spec.description or "ADR-068" in spec.formula


@pytest.mark.trace("REQ-WP-088")
def test_only_binance_is_flagged_as_having_sequential_trade_ids() -> None:
    """Measured on live bars: Binance ids are sequential; Bybit's are not numeric, OKX's are not."""
    flagged = {name for name, config in VENUE_REGISTRY.items() if config.sequential_trade_ids}

    assert flagged == {"binance"}
