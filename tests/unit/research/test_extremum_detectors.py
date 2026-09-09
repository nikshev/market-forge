"""EXP-011's structural extremum detector comparison (REQ-EXP-011)."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from channelflow.backtest import CostModel, CostsRequired
from channelflow.channels import RollingOLSChannel
from channelflow.extrema import ThresholdMode
from channelflow.research.extremum_detectors import (
    METHODS,
    compare_detectors,
    volatility_regime,
)
from tests.unit.channels.conftest import make_bar

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def swings(n: int = 600, *, period: int = 40, amp: float = 0.03, drift: float = 0.0002):
    """A market that swings on a fixed period, so extrema are countable by hand."""
    built = []
    for i in range(n):
        close = 100.0 * math.exp(amp * math.sin(2 * math.pi * i / period) + drift * i)
        bar = make_bar(index=i, close=close)
        built.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.002, 8))),
                    "low": Decimal(str(round(close * 0.998, 8))),
                }
            )
        )
    return built


def quiet_then_wild(n: int = 600):
    """Half a calm market, half a violent one, for the stability metric."""
    built = []
    for i in range(n):
        amp = 0.004 if i < n // 2 else 0.05
        close = 100.0 * math.exp(amp * math.sin(2 * math.pi * i / 40))
        bar = make_bar(index=i, close=close)
        built.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.002, 8))),
                    "low": Decimal(str(round(close * 0.998, 8))),
                }
            )
        )
    return built


@pytest.mark.trace("REQ-EXP-011")
def test_all_five_methods_are_compared() -> None:
    """EXP-011 names five, which are the threshold policy's five modes."""
    report = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())

    assert set(report.entries) == set(METHODS)
    assert len(METHODS) == 5


@pytest.mark.trace("REQ-EXP-011")
def test_every_metric_is_reported_for_a_method_that_fired() -> None:
    """EXP-011's five: lag, rate, prominence, regime stability, expectancy."""
    report = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())

    fired = [e for e in report.entries.values() if e.extrema > 0]
    assert fired
    for entry in fired:
        assert entry.median_lag_bars is not None
        assert entry.per_1000_bars > 0
        assert entry.regimes
        assert entry.regime_ratio is not None or any(r.extrema == 0 for r in entry.regimes)


@pytest.mark.trace("REQ-EXP-011")
def test_the_channel_mode_needs_a_channel_and_says_so() -> None:
    """Without one it cannot compute a threshold at all.

    Reported as a count of zero it would be indistinguishable from a method that
    ran and found nothing, and those mean opposite things.
    """
    report = compare_detectors(swings(), costs=COSTS, channel=None)

    entry = report.entries[ThresholdMode.CHANNEL_WIDTH_FRACTION]
    assert entry.extrema == 0
    assert "needs a channel width" in entry.reason


@pytest.mark.trace("REQ-EXP-011")
def test_the_channel_mode_fires_when_a_channel_is_supplied() -> None:
    """And the units are the channel's own.

    Read as a fraction of price rather than a percentage, a real 2% channel
    produces a 5,000 bps threshold, nothing is ever confirmed, and the report
    says the method found no extrema.
    """
    report = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())

    entry = report.entries[ThresholdMode.CHANNEL_WIDTH_FRACTION]
    assert entry.extrema > 0
    assert entry.reason == ""


@pytest.mark.trace("REQ-EXP-011")
def test_a_fixed_threshold_is_less_stable_across_regimes_than_an_adaptive_one() -> None:
    """The metric that decides most real arguments.

    A fixed threshold in basis points finds a swing every other bar in a storm
    and nothing in a drift. An adaptive one is supposed not to -- and the ratio
    between its two regimes is how that claim is checked rather than asserted.
    """
    report = compare_detectors(quiet_then_wild(), costs=COSTS, channel=RollingOLSChannel())

    fixed = report.entries[ThresholdMode.FIXED_BPS]
    adaptive = report.entries[ThresholdMode.ATR_MULTIPLE]
    if fixed.regime_ratio is None or adaptive.regime_ratio is None:
        pytest.skip("one method did not fire in both regimes on this fixture")
    assert fixed.regime_ratio >= adaptive.regime_ratio


@pytest.mark.trace("REQ-EXP-011")
def test_the_regimes_are_split_at_the_series_own_median() -> None:
    """Not into fixed halves: a series whose second half is quieter would have
    its "volatile" regime be the calm one, and the metric would report the
    opposite of what happened."""
    labels = volatility_regime(quiet_then_wild())

    assert set(labels) == {"calm", "volatile"}
    first_half = labels[: len(labels) // 2]
    assert first_half.count("calm") > first_half.count("volatile")


@pytest.mark.trace("REQ-EXP-011")
def test_an_extremum_belongs_to_the_regime_it_was_confirmed_in() -> None:
    """Not the regime it happened in. The confirmation is what a live system
    would have acted on, and the two can sit in different regimes."""
    report = compare_detectors(quiet_then_wild(), costs=COSTS, channel=RollingOLSChannel())

    for entry in report.entries.values():
        if entry.extrema == 0:
            continue
        assert sum(r.extrema for r in entry.regimes) == entry.extrema


@pytest.mark.trace("REQ-EXP-011")
def test_the_downstream_expectancy_is_after_costs() -> None:
    """EXP-011's fifth metric, and PRD §41 rule 9."""
    cheap = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())
    dear = compare_detectors(
        swings(),
        costs=CostModel(fee_bps=100.0, slippage_bps=100.0),
        channel=RollingOLSChannel(),
    )

    for method in METHODS:
        one, other = cheap.entries[method].expectancy, dear.entries[method].expectancy
        if one is None or other is None:
            continue
        assert other.expectancy_r < one.expectancy_r


@pytest.mark.trace("REQ-EXP-011")
def test_the_comparison_without_costs_is_refused() -> None:
    """Tested with no method at all, so only this refusal can fire."""
    with pytest.raises(CostsRequired):
        compare_detectors(swings(), costs=None, methods=())


@pytest.mark.trace("REQ-EXP-011")
def test_a_method_that_confirms_nothing_says_so() -> None:
    """Absent is not zero, here as everywhere."""
    from channelflow.extrema import ThresholdPolicy

    report = compare_detectors(
        swings(amp=0.001),
        costs=COSTS,
        methods=(ThresholdMode.FIXED_BPS,),
        policy=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=5000.0),
    )

    entry = report.entries[ThresholdMode.FIXED_BPS]
    assert entry.extrema == 0
    assert "no extremum was confirmed" in entry.reason


@pytest.mark.trace("REQ-EXP-011")
def test_nothing_is_ranked() -> None:
    """The five metrics pull against each other: a detector that confirms sooner
    confirms more and confirms noise. A single ranking would hide the trade-off
    the experiment exists to show."""
    report = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())

    assert not hasattr(report, "ranking")
    assert "pull against each other" in report.note


@pytest.mark.trace("REQ-EXP-011")
def test_two_runs_produce_equal_reports() -> None:
    bars = swings()

    assert compare_detectors(bars, costs=COSTS, channel=RollingOLSChannel()) == (
        compare_detectors(bars, costs=COSTS, channel=RollingOLSChannel())
    )


def mostly_quiet(n: int = 600):
    """Quiet for four fifths, wild for the last fifth.

    A median split labels half the bars each way whatever the shape; a split at
    the middle bar's own volatility lands deep inside the quiet stretch and calls
    almost everything volatile.
    """
    built = []
    for i in range(n):
        amp = 0.003 if i < int(n * 0.8) else 0.06
        close = 100.0 * math.exp(amp * math.sin(2 * math.pi * i / 40))
        bar = make_bar(index=i, close=close)
        built.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.002, 8))),
                    "low": Decimal(str(round(close * 0.998, 8))),
                }
            )
        )
    return built


@pytest.mark.trace("REQ-EXP-011")
def test_the_median_split_divides_the_series_in_half() -> None:
    """Whatever the shape. A cut taken from one bar's own volatility lands
    wherever that bar happened to be, and on a series that is quiet for four
    fifths it calls almost everything volatile."""
    labels = volatility_regime(mostly_quiet())

    share = labels.count("volatile") / len(labels)
    assert 0.3 < share < 0.7


@pytest.mark.trace("REQ-EXP-011")
def test_extrema_are_attributed_to_both_regimes() -> None:
    """A detector fires in the storm and in the drift, and the metric is the
    difference between them. Attributing everything to one regime makes the
    ratio meaningless while leaving every count plausible."""
    report = compare_detectors(quiet_then_wild(), costs=COSTS, channel=RollingOLSChannel())

    volatile_totals = sum(
        r.extrema
        for entry in report.entries.values()
        for r in entry.regimes
        if r.label == "volatile"
    )
    assert volatile_totals > 0


@pytest.mark.trace("REQ-EXP-011")
def test_the_regime_ratio_is_the_busier_over_the_quieter() -> None:
    """So it is never below one, and a bigger number always means less stable.

    Inverted it still ranks the methods -- in the opposite order -- and every
    comparison between them reads backwards.
    """
    report = compare_detectors(quiet_then_wild(), costs=COSTS, channel=RollingOLSChannel())

    ratios = [e.regime_ratio for e in report.entries.values() if e.regime_ratio is not None]
    assert ratios
    assert all(ratio >= 1.0 for ratio in ratios)


@pytest.mark.trace("REQ-EXP-011")
def test_a_confirmation_always_lags_its_extremum() -> None:
    """PRD §13A.1: the high happened at `extremum_time` and could not be known
    until the reversal crossed the threshold. A lag of zero would mean the
    detector confirmed on the extremum's own bar, which is the repaint the whole
    module exists to prevent."""
    report = compare_detectors(swings(), costs=COSTS, channel=RollingOLSChannel())

    lags = [e.median_lag_bars for e in report.entries.values() if e.median_lag_bars is not None]
    assert lags
    assert all(lag >= 1.0 for lag in lags)


def noisy(n: int = 600):
    """The same swings with a chop on top.

    A smooth sine turns twice per period whatever the threshold, so it cannot
    tell a sensible threshold from an absurdly small one. The chop can: a tiny
    threshold confirms on every wiggle.
    """
    built = []
    for i in range(n):
        close = 100.0 * math.exp(0.03 * math.sin(2 * math.pi * i / 40) + 0.004 * math.sin(i * 2.3))
        bar = make_bar(index=i, close=close)
        built.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.002, 8))),
                    "low": Decimal(str(round(close * 0.998, 8))),
                }
            )
        )
    return built


@pytest.mark.trace("REQ-EXP-011")
def test_the_channel_mode_uses_the_channels_own_width() -> None:
    """Not a constant standing in for it.

    On a choppy series the real width gives 45 confirmations per thousand bars,
    in line with every other method. A width fixed at some tiny value gives 235
    -- the detector confirming on each wiggle -- and every other metric stays
    plausible while the method becomes a different one.
    """
    report = compare_detectors(noisy(), costs=COSTS, channel=RollingOLSChannel())

    channel_rate = report.entries[ThresholdMode.CHANNEL_WIDTH_FRACTION].per_1000_bars
    atr_rate = report.entries[ThresholdMode.ATR_MULTIPLE].per_1000_bars
    assert atr_rate > 0
    assert channel_rate < atr_rate * 2.0
