"""PRD section 43's alert ranker and section 22.3's threshold (REQ-SCORE-001)."""

from __future__ import annotations

import pytest

from channelflow.scoring import (
    DEFAULT_ALERT_THRESHOLD,
    AlertThresholds,
    FactorOutOfRange,
    RankInput,
    rank,
    rank_score,
)


@pytest.mark.trace("REQ-SCORE-001")
def test_the_rank_score_is_the_prds_product() -> None:
    """SC-008, FR-012.

    Section 43, verbatim: `rank_score = setup_score * data_quality *
    liquidity_factor * novelty_factor`. 80 * 0.9 * 0.5 * 0.5 = 18.
    """
    assert rank_score(
        setup_score=80.0, data_quality=0.9, liquidity_factor=0.5, novelty_factor=0.5
    ) == pytest.approx(18.0)


@pytest.mark.trace("REQ-SCORE-001")
def test_an_illiquid_asset_cannot_rank_on_setup_quality_alone() -> None:
    """SC-008, FR-012.

    Section 43's stated purpose for the factor: it "prevents noisy illiquid
    assets dominating". A perfect setup on an asset nobody can trade ranks at
    zero, which is the multiplication doing its job rather than a special case.
    """
    assert rank_score(
        setup_score=100.0, data_quality=1.0, liquidity_factor=0.0, novelty_factor=1.0
    ) == pytest.approx(0.0)


@pytest.mark.trace("REQ-SCORE-001")
@pytest.mark.parametrize("factor", ["data_quality", "liquidity_factor", "novelty_factor"])
def test_a_factor_outside_its_range_is_refused(factor: str) -> None:
    """SC-008, FR-012.

    All three are penalties. Above 1 any of them becomes a bonus, and a stale,
    illiquid, repeated alert could outrank a fresh one.
    """
    kwargs = {
        "setup_score": 80.0,
        "data_quality": 1.0,
        "liquidity_factor": 1.0,
        "novelty_factor": 1.0,
    }
    kwargs[factor] = 1.5

    with pytest.raises(FactorOutOfRange, match=factor):
        rank_score(**kwargs)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-SCORE-001")
def test_ranking_orders_by_rank_score_descending() -> None:
    """SC-009, FR-013."""
    ranked = rank(
        [
            RankInput(key="ETHUSDT", setup_score=90.0, liquidity_factor=0.2),
            RankInput(key="BTCUSDT", setup_score=80.0, liquidity_factor=1.0),
        ]
    )

    assert [r.key for r in ranked] == ["BTCUSDT", "ETHUSDT"]


@pytest.mark.trace("REQ-SCORE-001")
def test_ranking_is_stable_across_input_orders() -> None:
    """SC-009, FR-013.

    Two candidates that tie must not swap places because the list was assembled
    differently. A market list that reorders itself between refreshes is one no
    reader can hold a position in.
    """
    tied = [
        RankInput(key="SOLUSDT", setup_score=80.0),
        RankInput(key="BTCUSDT", setup_score=80.0),
    ]

    forward = [r.key for r in rank(tied)]
    backward = [r.key for r in rank(list(reversed(tied)))]

    assert forward == backward == ["BTCUSDT", "SOLUSDT"]


@pytest.mark.trace("REQ-SCORE-001")
def test_the_default_threshold_is_the_prds_research_value() -> None:
    """SC-010, FR-014.

    Section 22.3: "Default research value only: `score >= 75`". The number is
    the PRD's; what matters is that it arrives labelled, so nobody reads it as a
    validated production threshold.
    """
    thresholds = AlertThresholds()

    resolved = thresholds.resolve(symbol="BTCUSDT", timeframe_ns=900_000_000_000, setup="upper")

    assert resolved.value == pytest.approx(DEFAULT_ALERT_THRESHOLD)
    assert resolved.value == pytest.approx(75.0)
    assert resolved.is_research_default


@pytest.mark.trace("REQ-SCORE-001")
def test_the_most_specific_override_wins() -> None:
    """SC-010, FR-014.

    Section 22.3 makes the threshold configurable "per symbol/timeframe/setup".
    With overrides at more than one specificity, a resolution that picked the
    first match found would depend on dictionary order.
    """
    thresholds = AlertThresholds(
        overrides={
            ("BTCUSDT", None, None): 70.0,
            ("BTCUSDT", 900_000_000_000, None): 80.0,
            ("BTCUSDT", 900_000_000_000, "upper"): 85.0,
        }
    )

    assert thresholds.resolve(
        symbol="BTCUSDT", timeframe_ns=900_000_000_000, setup="upper"
    ).value == pytest.approx(85.0)
    assert thresholds.resolve(
        symbol="BTCUSDT", timeframe_ns=900_000_000_000, setup="middle"
    ).value == pytest.approx(80.0)
    assert thresholds.resolve(
        symbol="BTCUSDT", timeframe_ns=60_000_000_000, setup="upper"
    ).value == pytest.approx(70.0)
    assert thresholds.resolve(
        symbol="ETHUSDT", timeframe_ns=60_000_000_000, setup="upper"
    ).value == pytest.approx(75.0)


@pytest.mark.trace("REQ-SCORE-001")
def test_an_override_is_no_longer_a_research_default() -> None:
    """FR-014.

    The label travels with the value. A configured 85 is somebody's decision;
    the 75 is the PRD's placeholder, and a reader has to be able to tell which
    one they are looking at.
    """
    thresholds = AlertThresholds(overrides={("BTCUSDT", None, None): 85.0})

    resolved = thresholds.resolve(symbol="BTCUSDT", timeframe_ns=1, setup="upper")

    assert not resolved.is_research_default


@pytest.mark.trace("REQ-SCORE-001")
def test_a_threshold_outside_the_score_range_is_refused() -> None:
    """FR-014.

    A threshold above 100 can never be met, and one below zero is always met.
    Both silently turn the alert gate into a constant.
    """
    with pytest.raises(ValueError, match="threshold"):
        AlertThresholds(overrides={("BTCUSDT", None, None): 120.0})


@pytest.mark.trace("REQ-SCORE-001")
def test_the_scoring_package_consults_no_clock() -> None:
    """SC-011, FR-015.

    A score that depends on when it was computed cannot be recomputed from a
    stored snapshot, and section 27.4's explanation panel is exactly that
    recomputation.
    """
    from pathlib import Path

    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "scoring"
    modules = list(package.glob("*.py"))
    assert modules, "the package moved; this test would otherwise pass by finding nothing"

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
