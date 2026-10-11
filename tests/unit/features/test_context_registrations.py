"""The three features the context pass writes say where their numbers come from (REQ-WP-093)."""

from __future__ import annotations

import pytest

from channelflow.features.registry import REGISTRY


@pytest.mark.trace("REQ-WP-093")
def test_open_interest_says_it_is_the_venues_usd_figure_of_the_venues_perpetual() -> None:
    spec = REGISTRY["open_interest_usd"]
    text = f"{spec.formula} {spec.null_policy}".lower()
    assert "perpetual" in text
    assert "stale" in text or "older than" in text


@pytest.mark.trace("REQ-WP-093")
def test_funding_z_says_it_reads_settled_history_only() -> None:
    spec = REGISTRY["funding_z"]
    text = f"{spec.formula} {spec.null_policy}".lower()
    assert "history" in text and "settle" in text
    assert "polled" in text  # and that polled estimates are excluded, by name


@pytest.mark.trace("REQ-WP-093")
def test_basis_says_it_is_the_perpetuals_mark_against_the_venues_index() -> None:
    spec = REGISTRY["basis_bps"]
    text = f"{spec.formula} {spec.description}".lower()
    assert "mark" in text and "index" in text


@pytest.mark.trace("REQ-WP-094")
def test_the_liquidation_sums_say_zero_needs_a_stream_that_was_listening() -> None:
    for name in ("liquidation_long_usd_5m", "liquidation_short_usd_5m"):
        spec = REGISTRY[name]
        text = f"{spec.formula} {spec.null_policy}".lower()
        assert "heartbeat" in text and "position" in text


@pytest.mark.trace("REQ-WP-094")
def test_the_imbalance_says_it_is_absent_for_a_window_nobody_watched() -> None:
    text = REGISTRY["liquidation_imbalance_5m"].null_policy.lower()
    assert "did not cover" in text


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize("name", ["liquidation_intensity_5m", "time_since_liquidation_spike"])
def test_the_two_liquidation_features_the_worker_does_not_write_say_so(name: str) -> None:
    assert "not produced" in REGISTRY[name].formula.lower()
