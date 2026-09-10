"""EXP-010's cross-venue divergence study (REQ-EXP-010)."""

from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.backtest import CostModel, CostsRequired
from channelflow.research.lead_lag_value import (
    DEFAULT_THRESHOLDS,
    DivergenceSignal,
    Verdict,
    evaluate_divergence,
)
from tests.unit.channels.conftest import make_bar

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def bars_with_moves(n: int = 400, *, move_every: int = 20, size: float = 0.02):
    """A series that jumps up two bars after each signal, and drifts otherwise.

    Two bars, not one: a signal at `i` fills at the open of `i + 1`, so a jump on
    that bar is already in the entry price and the trade catches nothing. The
    move has to happen after the fill for the signal to have predicted anything.
    """
    built = []
    level = 0.0
    for i in range(n):
        if i % move_every == 3:
            level += size
        close = 100.0 * math.exp(level + 0.001 * math.sin(i * 0.7))
        bar = make_bar(index=i, close=close)
        built.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.006, 8))),
                    "low": Decimal(str(round(close * 0.994, 8))),
                }
            )
        )
    return built


def predictive_signals(n: int = 400, *, move_every: int = 20):
    """A signal one bar before each move, pointing the right way."""
    return [
        DivergenceSignal(index=i, divergence_bps=50.0, direction="long")
        for i in range(n)
        if i % move_every == 0
    ]


@pytest.mark.trace("REQ-EXP-010")
def test_a_divergence_that_predicts_is_found_out_of_sample() -> None:
    """The control. Without a case that reaches `EDGE`, `NO_EDGE` everywhere
    would be consistent with a study that cannot conclude anything."""
    result = evaluate_divergence(
        bars_with_moves(),
        predictive_signals(),
        costs=COSTS,
        latency_bars=0,
        horizon_bars=5,
    )

    assert result.verdict is Verdict.EDGE
    assert result.out_of_sample is not None
    assert result.out_of_sample.expectancy_r > 0


@pytest.mark.trace("REQ-EXP-010")
def test_latency_can_destroy_the_edge() -> None:
    """The experiment's own question: "after realistic latency".

    The move here is over in two bars. Entering five bars late is entering after
    it, and a study without the delay would have reported the same edge as
    tradeable.
    """
    prompt = evaluate_divergence(
        bars_with_moves(), predictive_signals(), costs=COSTS, latency_bars=0, horizon_bars=5
    )
    delayed = evaluate_divergence(
        bars_with_moves(), predictive_signals(), costs=COSTS, latency_bars=5, horizon_bars=5
    )

    assert prompt.verdict is Verdict.EDGE
    assert delayed.out_of_sample is not None
    assert delayed.out_of_sample.expectancy_r < prompt.out_of_sample.expectancy_r  # type: ignore[union-attr]


@pytest.mark.trace("REQ-EXP-010")
def test_the_latency_has_no_default() -> None:
    """ "Realistic" is the caller's word about their infrastructure, and zero
    would be a claim this module has no business making."""
    import inspect

    parameter = inspect.signature(evaluate_divergence).parameters["latency_bars"]

    assert parameter.default is inspect.Parameter.empty


@pytest.mark.trace("REQ-EXP-010")
def test_a_negative_latency_is_refused() -> None:
    """A signal is not actionable before it exists."""
    with pytest.raises(ValueError, match="before it exists"):
        evaluate_divergence(bars_with_moves(), predictive_signals(), costs=COSTS, latency_bars=-1)


@pytest.mark.trace("REQ-EXP-010")
def test_the_threshold_is_chosen_in_sample_and_scored_out_of_sample() -> None:
    """PRD §41 rule 10. A threshold chosen on the data it is scored on always
    looks profitable, which is why §17.2 forbids the rule without OOS
    validation in the first place."""
    result = evaluate_divergence(
        bars_with_moves(),
        predictive_signals(),
        costs=COSTS,
        latency_bars=0,
        horizon_bars=5,
        test_fraction=0.3,
    )

    assert result.chosen_threshold_bps is not None
    assert result.in_sample is not None and result.out_of_sample is not None
    assert result.signals_in_sample > 0 and result.signals_out_of_sample > 0
    assert result.in_sample.trades > result.out_of_sample.trades


@pytest.mark.trace("REQ-EXP-010")
def test_noise_returns_no_edge_and_raises_nothing() -> None:
    """[[ADR-042]]'s pattern: a research result that raises is one that blocks."""
    noise = [
        DivergenceSignal(index=i, divergence_bps=50.0, direction="short") for i in range(0, 400, 20)
    ]

    result = evaluate_divergence(
        bars_with_moves(), noise, costs=COSTS, latency_bars=1, horizon_bars=5
    )

    assert result.verdict is Verdict.NO_EDGE
    assert result.reason


@pytest.mark.trace("REQ-EXP-010")
def test_signals_on_one_side_of_the_split_cannot_be_validated() -> None:
    """Choosing and scoring on one segment is the thing the experiment exists to
    avoid, so it reports rather than pretending."""
    early_only = [
        DivergenceSignal(index=i, divergence_bps=50.0, direction="long") for i in range(0, 100, 20)
    ]

    result = evaluate_divergence(
        bars_with_moves(), early_only, costs=COSTS, latency_bars=0, horizon_bars=5
    )

    assert result.verdict is Verdict.NO_EDGE
    assert "separate data" in result.reason


@pytest.mark.trace("REQ-EXP-010")
def test_the_study_without_costs_is_refused() -> None:
    """PRD §41 rule 9, and EXP-010 names costs in its own sentence."""
    with pytest.raises(CostsRequired):
        evaluate_divergence(bars_with_moves(), predictive_signals(), costs=None, latency_bars=0)


@pytest.mark.trace("REQ-EXP-010")
def test_raising_the_costs_lowers_the_out_of_sample_result() -> None:
    """The control for the costs reaching the arithmetic at all."""
    cheap = evaluate_divergence(
        bars_with_moves(), predictive_signals(), costs=COSTS, latency_bars=0, horizon_bars=5
    )
    dear = evaluate_divergence(
        bars_with_moves(),
        predictive_signals(),
        costs=CostModel(fee_bps=80.0, slippage_bps=80.0),
        latency_bars=0,
        horizon_bars=5,
    )

    assert cheap.out_of_sample is not None and dear.out_of_sample is not None
    assert dear.out_of_sample.expectancy_r < cheap.out_of_sample.expectancy_r


@pytest.mark.trace("REQ-EXP-010")
def test_the_signal_path_does_not_import_this_study() -> None:
    """[[ADR-040]]'s import ban, extended.

    §17.2 forbids converting a correlation into a trading rule without
    out-of-sample validation. This module *is* the validation, and a signal-path
    module importing it would be reaching for the conclusion rather than the
    evidence.
    """
    root = Path(__file__).resolve().parents[3] / "src" / "channelflow"

    for package in ("signals", "alerting", "stops", "extrema"):
        directory = root / package
        assert directory.is_dir(), f"{package} moved; this test would pass by finding nothing"
        for module in directory.glob("*.py"):
            imports = [
                line
                for line in module.read_text().splitlines()
                if line.startswith(("import ", "from "))
            ]
            assert not [line for line in imports if "lead_lag" in line or "leadlag" in line], (
                f"{package}/{module.name} imports the lead-lag study"
            )


@pytest.mark.trace("REQ-EXP-010")
def test_two_studies_produce_equal_results() -> None:
    bars, signals = bars_with_moves(), predictive_signals()

    first = evaluate_divergence(bars, signals, costs=COSTS, latency_bars=1, horizon_bars=5)
    second = evaluate_divergence(bars, signals, costs=COSTS, latency_bars=1, horizon_bars=5)

    assert first == second


@pytest.mark.trace("REQ-EXP-010")
def test_the_in_sample_score_counts_only_in_sample_signals() -> None:
    """The threshold must be chosen on the training half alone.

    Counting every signal while calling the result "in sample" is the leak §41
    rule 10 exists to stop, and it shows as a trade count that does not match the
    segment it claims to cover.
    """
    signals = predictive_signals()
    result = evaluate_divergence(
        bars_with_moves(),
        signals,
        costs=COSTS,
        latency_bars=0,
        horizon_bars=5,
        test_fraction=0.3,
    )

    split = int(400 * 0.7)
    early = [s for s in signals if s.index < split]
    assert result.in_sample is not None
    # Every early signal clears the chosen threshold here, and a handful at the
    # end of the segment have no room left for the horizon.
    assert result.in_sample.trades <= len(early)
    assert result.in_sample.trades > len(signals) - len(early)


@pytest.mark.trace("REQ-EXP-010")
def test_the_first_threshold_that_scores_best_is_kept() -> None:
    """Ties go to the narrower filter, and the scan must not simply keep the
    last one it tried.

    Every signal here carries 50 bps, so the thresholds at 5, 10, 20 and 40 all
    admit the same trades and score identically; 80 admits none. The chosen one
    is the first of the equals, not the last.
    """
    result = evaluate_divergence(
        bars_with_moves(), predictive_signals(), costs=COSTS, latency_bars=0, horizon_bars=5
    )

    assert result.chosen_threshold_bps == pytest.approx(5.0)


@pytest.mark.trace("REQ-EXP-010")
def test_a_short_divergence_is_traded_as_a_short() -> None:
    """A short's target sits below the fill.

    Read as a long's, every short signal aims at a price the market has to rise
    to reach -- and a study whose fixtures are all long would never notice.
    """
    falling = []
    level = 0.0
    for i in range(400):
        if i % 20 == 3:
            level -= 0.02
        close = 100.0 * math.exp(level + 0.001 * math.sin(i * 0.7))
        bar = make_bar(index=i, close=close)
        falling.append(
            bar.model_copy(
                update={
                    "open": Decimal(str(round(close, 8))),
                    "high": Decimal(str(round(close * 1.006, 8))),
                    "low": Decimal(str(round(close * 0.994, 8))),
                }
            )
        )
    shorts = [
        DivergenceSignal(index=i, divergence_bps=50.0, direction="short") for i in range(0, 400, 20)
    ]

    result = evaluate_divergence(falling, shorts, costs=COSTS, latency_bars=0, horizon_bars=5)

    assert result.verdict is Verdict.EDGE


@pytest.mark.trace("REQ-EXP-010")
def test_outcomes_that_are_all_ambiguous_report_rather_than_raise() -> None:
    """PRD §40's rule reaching this study: a bar spanning both levels says
    nothing, and a set of them says nothing at all -- which is a finding, not an
    exception out of the metric layer."""
    wide = [
        bar.model_copy(
            update={
                "high": Decimal(str(round(float(bar.close) * 1.20, 8))),
                "low": Decimal(str(round(float(bar.close) * 0.80, 8))),
            }
        )
        for bar in bars_with_moves()
    ]

    result = evaluate_divergence(
        wide, predictive_signals(), costs=COSTS, latency_bars=0, horizon_bars=5
    )

    assert result.verdict is Verdict.NO_EDGE
    assert "resolvable" in result.reason


@pytest.mark.trace("REQ-EXP-010")
def test_the_costs_refusal_fires_before_anything_is_scored() -> None:
    """With no signals at all, nothing downstream is reached -- so only this
    function's own refusal can raise, which is what makes it load-bearing rather
    than a restatement of the economics layer's."""
    with pytest.raises(CostsRequired):
        evaluate_divergence(bars_with_moves(), [], costs=None, latency_bars=0)


# --- the field the study chose from (REQ-BIAS-011) ---------------------------


@pytest.mark.trace("REQ-BIAS-011")
def test_every_threshold_swept_is_in_the_field() -> None:
    """EXP-010 is where PRD §41 rule 11 bites hardest.

    Five thresholds are tried in sample and one is carried out of sample; before
    this, the four that lost left no trace anywhere. A reader given only the
    winner cannot tell a threshold that beat four rivals from one that was the
    only one to resolve a trade at all.
    """
    result = evaluate_divergence(
        bars_with_moves(),
        predictive_signals(),
        costs=COSTS,
        latency_bars=0,
    )

    field = result.compared

    assert len(field.variants) == len(DEFAULT_THRESHOLDS)
    assert field.chosen == str(result.chosen_threshold_bps)
    assert {c["threshold_bps"] for c in field.variants.values()} == set(DEFAULT_THRESHOLDS)


@pytest.mark.trace("REQ-BIAS-011")
def test_a_study_that_could_not_choose_still_names_the_field_it_tried() -> None:
    """The early returns are where a field would be easiest to forget, and the
    run that chose nothing is exactly the one whose attempts are worth having:
    "we tried five and none resolved" is a finding, and an empty record is not.
    """
    result = evaluate_divergence(
        bars_with_moves(),
        [s for s in predictive_signals() if s.index < 50],
        costs=COSTS,
        latency_bars=0,
    )

    field = result.compared

    assert result.chosen_threshold_bps is None
    assert field.chosen is None
    assert len(field.variants) == len(DEFAULT_THRESHOLDS)
