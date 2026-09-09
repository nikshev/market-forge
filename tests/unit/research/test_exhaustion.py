"""EXP-014's two studies of order-flow exhaustion (REQ-EXP-014)."""

from __future__ import annotations

import math

import pytest

from channelflow.research.exhaustion import (
    BULLETS,
    EXPLAINS_AND_PREDICTS,
    EXPLAINS_ONLY,
    NEITHER,
    SIGNALS,
    WARMUP_BARS,
    NotEnoughHistory,
    ReadingRule,
    SeriesMissing,
    study_exhaustion,
    trailing_calls,
)

BARS = 200
TURNS = [20, 60, 100, 140, 180]
HORIZON = 5
WINDOW = 5
GAP = 10
QUANTILE = 0.8
RULE = ReadingRule(effect_floor=0.3, lift_floor=1.5)


def leading(bars: int = BARS) -> list[float]:
    """High in the bars running into each turn, and at it.

    The shape a useful exhaustion signal would have: whatever it measures builds
    up before the turn, so it is already high at a bar someone could act on.
    """
    return [1.0 if any(turn - HORIZON <= i <= turn for turn in TURNS) else 0.0 for i in range(bars)]


def trailing_only(bars: int = BARS) -> list[float]:
    """High only in the bars *after* each turn.

    EXP-014's warning made into a series. A window straddling the turn sees a
    large difference from the control bars -- the signal really is extreme
    around every turn -- and at the moment of the decision it is flat, because
    every bar it marks is a bar the turn has already happened on.
    """
    return [1.0 if any(turn < i <= turn + HORIZON for turn in TURNS) else 0.0 for i in range(bars)]


def unrelated(bars: int = BARS) -> list[float]:
    """A deterministic wave on a period no turn follows."""
    return [math.sin(i * 2.0 * math.pi / 7.0) for i in range(bars)]


def spike_at(offset: int, bars: int = BARS) -> list[float]:
    """One high bar exactly `offset` bars before each turn, and nothing else."""
    marks = {turn - offset for turn in TURNS}
    return [1.0 if i in marks else 0.0 for i in range(bars)]


def constant(bars: int = BARS) -> list[float]:
    """A signal that never moves. Nothing in it ever stands out."""
    return [3.0] * bars


def regime_shift(bars: int = BARS) -> list[float]:
    """Small values for the first half of the series, large ones for the second.

    The distribution of the whole series is nothing like the distribution of its
    first half, which is what makes a threshold taken from the whole visible.
    """
    return [(i % 10) / 10.0 if i < bars // 2 else 100.0 + (i % 10) / 10.0 for i in range(bars)]


def series(**shapes: list[float]) -> dict[str, list[float]]:
    """Every signal EXP-014 names, with the named ones given a shape."""
    built = {name: unrelated() for name in SIGNALS}
    built.update(shapes)
    return built


def run(**shapes: list[float]):
    return study_exhaustion(
        series(**shapes),
        TURNS,
        window_bars=WINDOW,
        horizon_bars=HORIZON,
        control_gap_bars=GAP,
        call_quantile=QUANTILE,
        rule=RULE,
    )


@pytest.mark.trace("REQ-EXP-014")
def test_every_bullet_the_prd_names_is_studied() -> None:
    """OFI sign and slope; CVD divergence; microprice deviation; spread
    widening; wall replenishment/cancellation; absorption."""
    assert tuple(BULLETS) == (
        "ofi",
        "cvd_divergence",
        "microprice_deviation",
        "spread_widening",
        "wall_replenishment_cancellation",
        "absorption",
    )

    report = run()

    assert set(report.signals) == set(SIGNALS)
    assert {study.bullet for study in report.signals.values()} == set(BULLETS)


@pytest.mark.trace("REQ-EXP-014")
def test_both_studies_are_reported_for_every_signal() -> None:
    """EXP-014's second sentence: the point-in-time experiment is a *repeat* of
    the conditional study, not a replacement for it. Reporting one would leave a
    reader to assume the other."""
    report = run()

    for study in report.signals.values():
        assert study.contemporaneous is not None
        assert study.predictive is not None
        assert study.predictive.decided_bars > 0


@pytest.mark.trace("REQ-EXP-014")
def test_the_conditional_arm_declares_itself_retrospective() -> None:
    """Its window straddles a turn that was labelled from bars which had not
    arrived when the window opened. The declaration is a field rather than a
    docstring because that is the thing a reader has to carry away."""
    report = run()

    for study in report.signals.values():
        assert study.contemporaneous.retrospective is True
    assert "retrospective" in report.note
    assert "cannot be read as evidence" in report.note


@pytest.mark.trace("REQ-EXP-014")
def test_a_signal_that_explains_but_does_not_forecast_is_named_as_such() -> None:
    """The finding EXP-014 exists to produce.

    `trailing_only` is extreme around every single turn and useless at every
    moment anyone could act. A study reporting only the conditional arm would
    call it the best signal in the set.
    """
    report = run(absorption=trailing_only())

    study = report.signals["absorption"]
    assert study.contemporaneous.effect_size is not None
    assert abs(study.contemporaneous.effect_size) >= RULE.effect_floor, "it does explain"
    assert study.reading == EXPLAINS_ONLY
    assert "absorption" in report.explains_but_does_not_predict


@pytest.mark.trace("REQ-EXP-014")
def test_a_signal_that_does_both_is_named_as_such() -> None:
    """The control. Without it, `EXPLAINS_ONLY` everywhere would be consistent
    with a predictive arm that can never conclude anything."""
    report = run(ofi_slope=leading())

    study = report.signals["ofi_slope"]
    assert study.reading == EXPLAINS_AND_PREDICTS
    assert study.predictive.lift is not None and study.predictive.lift >= RULE.lift_floor


@pytest.mark.trace("REQ-EXP-014")
def test_a_signal_related_to_nothing_is_named_as_such() -> None:
    """And the second control: a wave on a period no turn follows explains
    nothing and forecasts nothing.

    Its lift is 1.07 -- above one, and above one by arithmetic accident over
    forty calls. That number is why the rule has a floor rather than a
    comparison against one.
    """
    report = run()

    study = report.signals["spread_widening"]
    assert study.reading == NEITHER
    assert study.predictive.lift is not None and study.predictive.lift > 1.0


@pytest.mark.trace("REQ-EXP-014")
def test_the_two_arms_disagree_on_the_same_series() -> None:
    """Which is the entire point of running both.

    If the conditional and the predictive readings always agreed, the second
    study would be a more expensive way of printing the first.
    """
    report = run(absorption=trailing_only(), ofi_slope=leading())

    explains = report.signals["absorption"]
    forecasts = report.signals["ofi_slope"]
    assert explains.contemporaneous.effect_size is not None
    assert forecasts.contemporaneous.effect_size is not None
    assert explains.predictive.lift is not None
    assert forecasts.predictive.lift is not None
    assert explains.predictive.lift < 1.0 < forecasts.predictive.lift


@pytest.mark.trace("REQ-EXP-014")
def test_the_calling_threshold_reads_no_bar_at_or_after_the_decision() -> None:
    """Principle I, at the place it is easiest to lose.

    The calls made over a prefix must be exactly the calls the whole series
    makes at those same bars. A quantile taken over the whole series satisfies
    every other test in this file and fails this one -- and the precision it
    produces looks like skill.
    """
    # The fixture has to be able to tell the two apart: its second half sits a
    # hundred times higher than its first, so the quantile of the whole series
    # is nothing like the quantile of the prefix. On a series whose two halves
    # look alike -- most of the fixtures here -- both thresholds land on the
    # same number and a look-ahead is invisible.
    values = regime_shift(BARS)
    prefix = len(values) // 2

    over_prefix = trailing_calls(values[:prefix], call_quantile=QUANTILE)
    over_all = [index for index in trailing_calls(values, call_quantile=QUANTILE) if index < prefix]

    assert over_prefix == over_all
    assert over_prefix, "the fixture has to produce calls for the equality to mean anything"


@pytest.mark.trace("REQ-EXP-014")
def test_the_predictive_arm_decides_only_bars_with_a_full_horizon_ahead() -> None:
    """A bar whose horizon runs past the end of the series has no answer.

    "No turn followed" there is a fact about where the data stops, and counting
    it as a miss teaches the study that the end of every dataset is quiet.
    """
    report = run()

    predictive = report.signals["absorption"].predictive
    assert predictive.warmup_bars == WARMUP_BARS
    assert predictive.decided_bars == BARS - HORIZON - WARMUP_BARS


@pytest.mark.trace("REQ-EXP-014")
def test_a_series_too_short_to_decide_anything_is_refused() -> None:
    """Rather than reported as a study that found nothing."""
    short = {name: [0.0, 1.0, 2.0, 3.0] for name in SIGNALS}

    with pytest.raises(NotEnoughHistory):
        study_exhaustion(
            short,
            [1],
            window_bars=WINDOW,
            horizon_bars=HORIZON,
            control_gap_bars=GAP,
            call_quantile=QUANTILE,
            rule=RULE,
        )


@pytest.mark.trace("REQ-EXP-014")
def test_a_missing_signal_is_refused() -> None:
    """A series read as zeros would report "this signal does nothing" about a
    signal nobody measured."""
    incomplete = series()
    incomplete.pop("wall_replenishment")

    with pytest.raises(SeriesMissing, match="wall_replenishment"):
        study_exhaustion(
            incomplete,
            TURNS,
            window_bars=WINDOW,
            horizon_bars=HORIZON,
            control_gap_bars=GAP,
            call_quantile=QUANTILE,
            rule=RULE,
        )


@pytest.mark.trace("REQ-EXP-014")
def test_the_research_judgements_are_required_and_bounded() -> None:
    """Five numbers decide what this study concludes and none of them has a
    default. PRD section 13A.27's warning applies to every one."""
    with pytest.raises(TypeError):
        study_exhaustion(series(), TURNS)  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="outside"):
        study_exhaustion(
            series(),
            TURNS,
            window_bars=WINDOW,
            horizon_bars=HORIZON,
            control_gap_bars=GAP,
            call_quantile=1.0,
            rule=RULE,
        )

    with pytest.raises(ValueError, match="effect_floor"):
        ReadingRule(effect_floor=0.0, lift_floor=1.5)

    with pytest.raises(ValueError, match="lift_floor"):
        ReadingRule(effect_floor=0.3, lift_floor=1.0)


@pytest.mark.trace("REQ-EXP-014")
def test_an_extremum_outside_the_series_is_refused() -> None:
    with pytest.raises(ValueError, match="outside the series"):
        study_exhaustion(
            series(),
            [*TURNS, BARS + 5],
            window_bars=WINDOW,
            horizon_bars=HORIZON,
            control_gap_bars=GAP,
            call_quantile=QUANTILE,
            rule=RULE,
        )


@pytest.mark.trace("REQ-EXP-014")
def test_control_bars_are_kept_away_from_every_turn() -> None:
    """A control bar next to a turn is half a turn bar, and it drags the
    comparison toward reporting no difference."""
    report = run(absorption=trailing_only())

    around = report.signals["absorption"].contemporaneous
    assert around.control_bars > 0
    # Every bar within the gap of a turn is excluded, and the gap is wider than
    # the window, so the control side cannot contain a bar the window used.
    excluded = {i for turn in TURNS for i in range(turn - GAP, turn + GAP + 1)}
    assert around.control_bars == BARS - len({i for i in excluded if 0 <= i < BARS})


@pytest.mark.trace("REQ-EXP-014")
def test_two_runs_produce_equal_reports() -> None:
    first = run(absorption=trailing_only(), ofi_slope=leading())
    second = run(absorption=trailing_only(), ofi_slope=leading())

    assert first.signals == second.signals
    assert first.note == second.note


@pytest.mark.trace("REQ-EXP-014")
def test_the_horizon_includes_its_own_last_bar() -> None:
    """A call exactly `horizon` bars before a turn is a hit; one bar earlier is
    not.

    Off by one here costs the study the calls furthest ahead of the turn --
    which are the ones a forecast is actually worth something for -- and the
    remaining precision still reads as a plausible number.
    """
    on_the_edge = run(cvd_divergence=spike_at(HORIZON))
    just_outside = run(cvd_divergence=spike_at(HORIZON + 1))

    inside = on_the_edge.signals["cvd_divergence"].predictive
    outside = just_outside.signals["cvd_divergence"].predictive
    assert inside.calls == len(TURNS)
    assert inside.hits == len(TURNS)
    assert outside.calls == len(TURNS)
    assert outside.hits == 0


@pytest.mark.trace("REQ-EXP-014")
def test_a_signal_that_never_stands_out_has_no_precision() -> None:
    """Precision over no calls is not zero, and a signal that never fires is not
    a signal that fires wrongly.

    Zero there would put a flat signal below a signal that called ten bars and
    got two right, which is backwards: one of them was measured.
    """
    report = run(microprice_deviation=constant())

    predictive = report.signals["microprice_deviation"].predictive
    assert predictive.calls == 0
    assert predictive.precision is None
    assert predictive.lift is None
    assert report.signals["microprice_deviation"].reading == NEITHER
