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


def a_function() -> None:
    """One half of the qualified-name collision case below."""


def _other_module_function() -> object:
    """A function with the same qualified name as `a_function`, from elsewhere.

    Built rather than imported: nothing in the repository happens to collide
    today, and waiting for one to appear is how the module prefix would be
    dropped as unused.
    """
    source = "def a_function() -> None: ...\n"
    namespace: dict[str, object] = {"__name__": "another.module"}
    exec(compile(source, "<another.module>", "exec"), namespace)  # noqa: S102
    return namespace["a_function"]


@dataclass(frozen=True)
class Comparison:
    """Stands in for the eighteen. The seam must not know any of them."""

    compared: Field


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
def test_a_variant_that_is_not_a_dataclass_reports_what_it_exposes() -> None:
    """The models are protocols, so a caller's variant need not be a dataclass.
    Refusing one would narrow a working API to serve a bookkeeping rule -- and
    `compare_channel_models` has a test that passes exactly such a stub."""

    class Stub:
        def __init__(self) -> None:
            self.lookback = 60
            self._scratch = "not configuration"

    config = config_of(Stub())

    assert config == {"variant": "Stub", "lookback": 60}


@pytest.mark.trace("REQ-BIAS-011")
def test_enum_variants_do_not_all_share_one_config() -> None:
    """EXP-009's field is an enum, and an enum member keeps its identity in a
    private attribute. Reading only public state gave all three corridor methods
    the same config -- the same failure the model-name design would have caused,
    reached from the other side."""
    from channelflow.research.corridor_calibration import Method

    configs = [config_of(method) for method in Method]

    assert len({tuple(sorted(c.items())) for c in configs}) == len(configs)


@pytest.mark.trace("REQ-BIAS-011")
def test_a_variant_holding_a_closure_hashes_the_same_on_the_next_run() -> None:
    """Found by a test going red, not by reading.

    EXP-012's turning methods carry a closure built fresh per call, so keeping
    the function object made two identical runs produce two different configs --
    and an identity that changes between identical runs is not an identity.
    `hashing.py` had already written down this failure's shape for `repr`; it
    arrives here through a dataclass field instead.
    """
    from channelflow.research.derivative_turning import default_methods

    first, second = default_methods(), default_methods()

    assert [config_of(m) for m in first] == [config_of(m) for m in second]
    assert len({config_of(m)["name"] for m in first}) == len(first)


@pytest.mark.trace("REQ-BIAS-011")
def test_two_functions_of_one_name_in_different_modules_do_not_collide() -> None:
    """The module travels with the qualified name because the qualified name is
    not unique on its own -- two research modules can each define a `slopes`
    closure inside a factory of the same name, and merging them would record two
    different variants as one run."""

    @dataclass(frozen=True)
    class Holder:
        fn: object

    one = config_of(Holder(fn=a_function))
    other = config_of(Holder(fn=_other_module_function()))

    assert one != other


@pytest.mark.trace("REQ-BIAS-011")
def test_a_callable_nested_inside_a_config_is_stabilised_too() -> None:
    """A variant can hold its behaviour one level down -- in a dict of options,
    or a tuple of stages -- and a function object there changes on every run
    just as surely as one at the top level."""

    @dataclass(frozen=True)
    class Nested:
        options: dict[str, object]
        stages: tuple[object, ...]

    def build() -> Nested:
        def inner() -> None: ...

        return Nested(options={"fn": inner}, stages=(inner,))

    assert config_of(build()) == config_of(build())


@pytest.mark.trace("REQ-BIAS-011")
def test_a_variant_that_exposes_nothing_is_identified_by_its_type_alone() -> None:
    """The honest limit of `config_of`, and it is worth a test rather than only
    a docstring: two such objects that differ are recorded as one run, because
    nothing they expose says otherwise."""
    assert config_of(object()) == {"variant": "object"}


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
    result = report(Comparison(compared=a_field()), registry, code)

    assert result.recorded == 3
    assert len(registry.runs()) == 3
    assert {run.variant for run in registry.runs()} == {"a", "b", "c"}


@pytest.mark.trace("REQ-BIAS-011")
def test_the_chosen_variant_is_the_only_one_kept(registry: Registry, code: CodeVersion) -> None:
    """A registry that recorded every variant as kept would record the field and
    lose the choice, which is half of what makes it checkable."""
    report(Comparison(compared=a_field(chosen="b")), registry, code)

    outcomes = {run.variant: run.outcome for run in registry.runs()}
    assert outcomes == {"a": Outcome.DISCARDED, "b": Outcome.KEPT, "c": Outcome.DISCARDED}


@pytest.mark.trace("REQ-BIAS-011")
def test_variants_that_differed_get_different_identities(
    registry: Registry, code: CodeVersion
) -> None:
    """Same dataset, same code, same model -- so the config is the only thing
    that can tell two variants apart, and it has to."""
    report(Comparison(compared=a_field()), registry, code)

    assert len(registry.hashes()) == 3


@pytest.mark.trace("REQ-BIAS-011")
def test_a_comparison_that_chose_nothing_records_and_reports_nothing(
    registry: Registry, code: CodeVersion
) -> None:
    """The field is on record; no winner is claimed, because none was."""
    result = report(Comparison(compared=a_field(chosen=None)), registry, code)

    assert result.recorded == 3
    assert result.report is None
    assert len(registry.runs()) == 3


@pytest.mark.trace("REQ-BIAS-011")
def test_a_chosen_variant_goes_through_the_gate(registry: Registry, code: CodeVersion) -> None:
    """Unchanged: this feature adopts REQ-REPRO-001's gate, it does not add one."""
    result = report(Comparison(compared=a_field(chosen="b")), registry, code)

    assert result.report is not None
    assert result.report.winner == "b"
    assert set(result.report.field) == {"a", "b", "c"}


@pytest.mark.trace("REQ-BIAS-011")
def test_an_unreproducible_run_is_recorded_and_refused(registry: Registry) -> None:
    """Both halves. Recording is unconditional (ADR-054), and the gate still
    refuses the report -- a dirty tree makes a result unreportable."""
    dirty = CodeVersion(commit=COMMIT, dirty=True)

    with pytest.raises(NotReproducible):
        report(Comparison(compared=a_field()), registry, dirty)

    assert len(registry.runs()) == 3
    assert all(not run.reproducible for run in registry.runs())


@pytest.mark.trace("REQ-BIAS-011")
def test_reporting_one_field_twice_does_not_double_it(
    registry: Registry, code: CodeVersion
) -> None:
    """ADR-056 on a registry. The plane rejects nothing, so the writer has to --
    and a run hash covers all four components, so two runs sharing one are the
    same run by construction."""
    comparison = Comparison(compared=a_field())

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
        report(Comparison(compared=field), registry, code)


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
