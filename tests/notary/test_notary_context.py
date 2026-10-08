# @trace: REQ-INFRA-007
"""The context a record is bound to: config hash, input dataset, code commit (FR-001, FR-010)."""

from __future__ import annotations

import dataclasses
import re

import pytest

from channelflow.backtest import BacktestRunner
from channelflow.channels.rolling_ols import RollingOLSChannel
from channelflow.experiments import dataset_reference
from channelflow.notary.context import CONFIG_FIELDS, STATE_FIELDS, build_context, pass_config
from channelflow.signals import Candidate, CandidateState, SignalMachine, Transition
from channelflow.signals.rejection import CloseBackInside

COMMIT = "0123456789abcdef0123456789abcdef01234567"
DATASET = (14_020, "96f5ba7db274aa80" * 4)


def context(runner: BacktestRunner | None = None, **overrides: object):  # type: ignore[no-untyped-def]
    args: dict[str, object] = {
        "gap_threshold": 1,
        "dataset": DATASET,
        "code_commit": COMMIT,
        "code_dirty": "false",
    }
    args.update(overrides)
    return build_context(runner or BacktestRunner(), **args)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-INFRA-007")
def test_every_field_of_every_component_is_classified_as_configuration_or_as_state() -> None:
    """The completeness test: a parameter added tomorrow and not classified fails here.

    Without it, a new field would silently stay out of the config hash -- which is the way a hash
    that claims to bind the configuration stops doing so.
    """
    runner = BacktestRunner()
    components = {
        RollingOLSChannel: {f.name for f in dataclasses.fields(runner.channel)},
        SignalMachine: {f.name for f in dataclasses.fields(runner.machine)},
        CloseBackInside: set(vars(runner.machine.detector)),
    }
    for cls, actual in components.items():
        config, state = set(CONFIG_FIELDS[cls]), set(STATE_FIELDS[cls])
        assert not (config & state), f"{cls.__name__}: {sorted(config & state)} is both"
        assert config | state == actual, (
            f"{cls.__name__}: unclassified {sorted(actual - config - state)}, "
            f"stale {sorted((config | state) - actual)}"
        )


def _variants() -> list[tuple[str, BacktestRunner]]:
    base = BacktestRunner()
    machine, channel = base.machine, base.channel

    def with_channel(**kw: object) -> BacktestRunner:
        return dataclasses.replace(base, channel=dataclasses.replace(channel, **kw))  # type: ignore[arg-type]

    def with_machine(**kw: object) -> BacktestRunner:
        return dataclasses.replace(base, machine=dataclasses.replace(machine, **kw))  # type: ignore[arg-type]

    return [
        ("channel.lookback", with_channel(lookback=61)),
        ("channel.min_window_bars", with_channel(min_window_bars=20)),
        ("channel.quantile_low", with_channel(quantile_low=0.2)),
        ("channel.quantile_high", with_channel(quantile_high=0.8)),
        ("channel.bands", with_channel(bands="sigma")),
        ("channel.band_sigmas", with_channel(band_sigmas=2.0)),
        ("machine.zone_upper", with_machine(zone_upper=(0.9, 1.0))),
        ("machine.zone_lower", with_machine(zone_lower=(0.0, 0.1))),
        ("machine.zone_middle", with_machine(zone_middle=(0.4, 0.6))),
        ("machine.overshoot_tolerance", with_machine(overshoot_tolerance=0.1)),
        ("machine.min_quality", with_machine(min_quality=0.6)),
        ("machine.slope_threshold", with_machine(slope_threshold=0.1)),
        ("machine.expiry_bars", with_machine(expiry_bars=20)),
        ("machine.opens", with_machine(opens=(("upper", "short"),))),
        ("detector.min_distance", with_machine(detector=CloseBackInside(0.3))),
    ]


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(("name", "runner"), _variants(), ids=[n for n, _ in _variants()])
def test_changing_any_configuration_field_changes_the_config_hash(
    name: str, runner: BacktestRunner
) -> None:
    assert context(runner).config_hash != context().config_hash, name


@pytest.mark.trace("REQ-INFRA-007")
def test_the_gap_threshold_setting_is_part_of_the_config() -> None:
    assert context(gap_threshold=2).config_hash != context(gap_threshold=1).config_hash


@pytest.mark.trace("REQ-INFRA-007")
def test_the_machines_state_is_not_part_of_the_config() -> None:
    """The machine changes `candidate` on every bar; a hash that included it would be a different
    hash for every record and would bind nothing."""
    runner = BacktestRunner()
    before = context(runner).config_hash
    runner.machine.candidate = Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=60,
        direction="short",
        boundary="upper",
        state=CandidateState.APPROACH,
        opened_at_ns=1,
        bars_since_open=1,
        history=(
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=1,
                reason="entered",
            ),
        ),
    )
    runner.machine._awaiting_zone_exit = True
    assert context(runner).config_hash == before


@pytest.mark.trace("REQ-INFRA-007")
def test_the_config_names_the_class_of_each_component() -> None:
    config = pass_config(BacktestRunner(), gap_threshold=1)
    assert config["channel"]["class"] == "RollingOLSChannel"  # type: ignore[index]
    assert config["machine"]["detector"]["class"] == "CloseBackInside"  # type: ignore[index]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_dataset_reference_is_the_repositorys_over_the_pinned_bars_snapshot() -> None:
    ctx = context()
    assert ctx.dataset_ref == dataset_reference({"bars": DATASET})
    assert ctx.dataset_snapshot_id == 14_020
    assert ctx.notarizable and ctx.reason is None


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"code_commit": None}, "commit"),
        ({"code_commit": ""}, "commit"),
        ({"code_commit": "abc123"}, "commit"),
        ({"code_commit": COMMIT.upper()}, "commit"),
        ({"code_dirty": "true"}, "dirty"),
        ({"code_dirty": "unknown"}, "dirty"),
        ({"code_dirty": None}, "dirty"),
    ],
)
def test_an_absent_malformed_or_dirty_commit_makes_the_context_unnotarizable_with_the_reason(
    overrides: dict[str, object], reason: str
) -> None:
    ctx = context(**overrides)
    assert not ctx.notarizable
    assert reason in (ctx.reason or "")
    assert ctx.code_commit == ""  # never a blank or doubtful value passed off as a commit


@pytest.mark.trace("REQ-INFRA-007")
def test_a_config_value_that_cannot_be_hashed_makes_it_unnotarizable_never_skipped() -> None:
    runner = BacktestRunner()
    runner.machine.opens = (object(),)  # type: ignore[assignment]
    ctx = context(runner)
    assert not ctx.notarizable
    assert re.search(r"config", ctx.reason or "")
    assert ctx.config_hash == ""


class _UnclassifiedDetector:
    """A rejection detector the notary has never been told how to hash."""

    name = "unclassified"

    def rejected(self, *args: object, **kwargs: object) -> bool:
        return False


@pytest.mark.trace("REQ-INFRA-007")
def test_a_component_nobody_classified_makes_the_context_unnotarizable_and_names_it() -> None:
    """A new detector is a new class; hashing 'whatever it happens to hold' is how a config hash
    quietly stops binding the configuration. The context says what is missing instead."""
    runner = BacktestRunner()
    runner.machine.detector = _UnclassifiedDetector()  # type: ignore[assignment]
    ctx = context(runner)
    assert not ctx.notarizable
    assert "_UnclassifiedDetector" in (ctx.reason or "") and "CONFIG_FIELDS" in (ctx.reason or "")
