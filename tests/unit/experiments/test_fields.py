"""A comparison names its field, and the seam records it (REQ-BIAS-011)."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pytest

from channelflow.experiments import (
    CherryPicked,
    CodeVersion,
    Field,
    NotReproducible,
    Outcome,
    Registry,
    Reported,
    UnhashableConfig,
    config_of,
    publish,
    report_comparison,
)
from channelflow.research import MODELS

from .conftest import COMMIT, dataset, identity


@dataclass(frozen=True)
class Comparison:
    """Stands in for the eighteen. The seam must not know any of them."""

    field: Field


def a_field(*, chosen: str | None = "b", n: int = 3) -> Field:
    return Field(
        variants={name: {"lookback": 60, "variant": name} for name in "abc"[:n]},
        chosen=chosen,
    )


@pytest.fixture
def code() -> CodeVersion:
    return CodeVersion(commit=COMMIT, dirty=False)


def report(comparison: Comparison, registry: Registry, code: CodeVersion, **kw: object) -> Reported:
    return report_comparison(
        comparison,
        experiment="EXP-001",
        dataset=dataset(),
        code=code,  # type: ignore[arg-type]
        registry=registry,
        as_of_ns=10,
        **kw,  # type: ignore[arg-type]
    )


# --- the field itself -------------------------------------------------------


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_of_nothing_is_refused() -> None:
    """A comparison of nothing is not a comparison, and a field of zero would
    pass the gate vacuously -- every variant in it is on record."""
    with pytest.raises(ValueError, match="no variants"):
        Field(variants={}, chosen=None)


@pytest.mark.trace("REQ-BIAS-011")
def test_a_winner_outside_its_own_field_cannot_be_constructed() -> None:
    """The gate refuses this already. Catching it here means a comparison cannot
    build the refusal in the first place."""
    with pytest.raises(ValueError, match="not among"):
        Field(variants={"a": {"x": 1}}, chosen="b")


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_may_choose_nothing() -> None:
    """Several experiments deliberately report a whole field and no choice.
    Forcing a winner would manufacture the claim rule 11 exists to check."""
    field = Field(variants={"a": {"x": 1}, "b": {"x": 2}}, chosen=None)

    assert field.chosen is None
    assert len(field.variants) == 2


# --- a variant's configuration ---------------------------------------------


@pytest.mark.trace("REQ-BIAS-011")
def test_two_variants_of_one_class_do_not_share_a_config() -> None:
    """The check that decided the design.

    Two of EXP-001's five models are one class under two band options. Hashing
    the variant's *name* would have given them one config and put two
    indistinguishable rows in the registry -- full coverage by row count, and
    worthless.
    """
    std = config_of(MODELS["rolling_ols_std_bands"])
    residual = config_of(MODELS["rolling_ols_residual_quantiles"])

    assert std != residual
    assert std["bands"] == "std"
    assert residual["bands"] == "residual_quantiles"


@pytest.mark.trace("REQ-BIAS-011")
def test_a_config_names_the_class_it_came_from() -> None:
    """Two dataclasses can carry identical fields and mean different things."""
    assert config_of(MODELS["kalman"])["variant"] == "KalmanChannel"


@pytest.mark.trace("REQ-BIAS-011")
def test_a_variant_that_is_not_a_dataclass_is_refused() -> None:
    """A variant recorded under a blank config would say the run had none."""
    with pytest.raises(UnhashableConfig, match="configuration"):
        config_of(object())


@pytest.mark.trace("REQ-BIAS-011")
def test_the_class_of_a_variant_is_refused_as_a_variant() -> None:
    """A plausible slip -- `RollingOLSChannel` rather than an instance of it --
    and `is_dataclass` says yes to both. A class has not been constructed, so it
    has no configuration to record."""
    with pytest.raises(UnhashableConfig, match="the class, not a variant"):
        config_of(type(MODELS["kalman"]))


@pytest.mark.trace("REQ-BIAS-011")
def test_every_field_of_a_variant_survives_into_its_config() -> None:
    """A config that dropped a field would make two runs that differed in it
    look like one run."""
    model = MODELS["huber_mad"]

    config = config_of(model)

    for name, value in dataclasses.asdict(model).items():
        assert config[name] == value


# --- the seam ---------------------------------------------------------------


@pytest.mark.trace("REQ-BIAS-011")
def test_every_variant_reaches_the_registry(registry: Registry, code: CodeVersion) -> None:
    """Rule 11 itself: the discarded ones are the reason the rule exists."""
    result = report(Comparison(field=a_field()), registry, code)

    assert result.recorded == 3
    assert len(registry.runs()) == 3
    assert {run.variant for run in registry.runs()} == {"a", "b", "c"}


@pytest.mark.trace("REQ-BIAS-011")
def test_the_chosen_variant_is_the_only_one_kept(registry: Registry, code: CodeVersion) -> None:
    """A registry that recorded every variant as kept would record the field and
    lose the choice, which is half of what makes it checkable."""
    report(Comparison(field=a_field(chosen="b")), registry, code)

    outcomes = {run.variant: run.outcome for run in registry.runs()}
    assert outcomes == {"a": Outcome.DISCARDED, "b": Outcome.KEPT, "c": Outcome.DISCARDED}


@pytest.mark.trace("REQ-BIAS-011")
def test_variants_that_differed_get_different_identities(
    registry: Registry, code: CodeVersion
) -> None:
    """Same dataset, same code, same model -- so the config is the only thing
    that can tell two variants apart, and it has to."""
    report(Comparison(field=a_field()), registry, code)

    assert len(registry.hashes()) == 3


@pytest.mark.trace("REQ-BIAS-011")
def test_a_comparison_that_chose_nothing_records_and_reports_nothing(
    registry: Registry, code: CodeVersion
) -> None:
    """The field is on record; no winner is claimed, because none was."""
    result = report(Comparison(field=a_field(chosen=None)), registry, code)

    assert result.recorded == 3
    assert result.report is None
    assert len(registry.runs()) == 3


@pytest.mark.trace("REQ-BIAS-011")
def test_a_chosen_variant_goes_through_the_gate(registry: Registry, code: CodeVersion) -> None:
    """Unchanged: this feature adopts REQ-REPRO-001's gate, it does not add one."""
    result = report(Comparison(field=a_field(chosen="b")), registry, code)

    assert result.report is not None
    assert result.report.winner == "b"
    assert set(result.report.field) == {"a", "b", "c"}


@pytest.mark.trace("REQ-BIAS-011")
def test_an_unreproducible_run_is_recorded_and_refused(registry: Registry) -> None:
    """Both halves. Recording is unconditional (ADR-054), and the gate still
    refuses the report -- a dirty tree makes a result unreportable."""
    dirty = CodeVersion(commit=COMMIT, dirty=True)

    with pytest.raises(NotReproducible):
        report(Comparison(field=a_field()), registry, dirty)

    assert len(registry.runs()) == 3
    assert all(not run.reproducible for run in registry.runs())


@pytest.mark.trace("REQ-BIAS-011")
def test_reporting_one_field_twice_does_not_double_it(
    registry: Registry, code: CodeVersion
) -> None:
    """ADR-056 on a registry. The plane rejects nothing, so the writer has to --
    and a run hash covers all four components, so two runs sharing one are the
    same run by construction."""
    comparison = Comparison(field=a_field())

    first = report(comparison, registry, code)
    second = report(comparison, registry, code)

    assert first.recorded == 3
    assert second.recorded == 0
    assert second.skipped == 3
    assert len(registry.runs()) == 3


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_whose_config_cannot_be_hashed_is_refused(
    registry: Registry, code: CodeVersion
) -> None:
    """Rather than recorded under a config of "", which would say the run had
    no configuration at all."""
    field = Field(variants={"a": {"model": object()}}, chosen=None)

    with pytest.raises(UnhashableConfig):
        report(Comparison(field=field), registry, code)


@pytest.mark.trace("REQ-BIAS-011")
def test_a_winner_missing_from_the_registry_is_still_refused(
    registry: Registry, code: CodeVersion
) -> None:
    """The seam records before it publishes, so this cannot happen through the
    seam. It is the gate's own refusal, and it stays reachable for a caller who
    assembles a field by hand."""
    with pytest.raises(CherryPicked, match="registry"):
        publish(
            experiment="EXP-001",
            winner="a",
            identity=identity(),
            considered=[("a", identity())],
            registry=registry,
        )
