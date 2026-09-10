"""Every experiment can name its field (REQ-BIAS-011).

[[ADR-054]] recorded that PRD §41 rule 11 was "enforceable and not yet
enforced". This module is what makes the difference permanent rather than a
snapshot: eighteen modules adopting today says nothing about the nineteenth, and
a hand-maintained list of what to check is a thing someone forgets.

So the package is **discovered**. Adding a module to `channelflow.research` is
enough to be checked, and the only way out is to declare a field -- which a
module that compares nothing cannot honestly do, and which a module that does
compare can.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass

import pytest

import channelflow.research
from channelflow.experiments import Field


@dataclass(frozen=True)
class Declaration:
    """What one research module says about itself."""

    module: str
    experiment: str
    comparison: type


def declarations() -> list[Declaration]:
    """Every module in the research package, and what it declares.

    A module missing either constant raises here rather than being skipped: a
    skip is how an unchecked module would look if the check were written the
    obvious way.
    """
    found: list[Declaration] = []
    for info in pkgutil.iter_modules(channelflow.research.__path__):
        module = importlib.import_module(f"channelflow.research.{info.name}")
        experiment = getattr(module, "EXPERIMENT", None)
        comparison = getattr(module, "COMPARISON", None)
        if experiment is None or comparison is None:
            raise AssertionError(
                f"channelflow.research.{info.name} declares no "
                f"{'EXPERIMENT' if experiment is None else 'COMPARISON'}. "
                "PRD section 41 rule 11 asks for every discarded variant to be "
                "stored; a module that cannot name its field cannot put one on "
                "record, and nothing else in the suite would notice"
            )
        found.append(Declaration(module=info.name, experiment=experiment, comparison=comparison))
    return found


@pytest.mark.trace("REQ-BIAS-011")
def test_every_research_module_declares_its_experiment_and_comparison() -> None:
    """The check that keeps the rule enforced after today."""
    found = declarations()

    assert found, "the research package went empty, which is not what this asserts"
    assert len(found) == len(list(pkgutil.iter_modules(channelflow.research.__path__)))


@pytest.mark.trace("REQ-BIAS-011")
@pytest.mark.parametrize("declaration", declarations(), ids=lambda d: d.module)
def test_every_comparison_can_name_its_field(declaration: Declaration) -> None:
    """The check a new comparison meets without this file being touched.

    Not `issubclass(comparison, Compared)`: `compared` is a property, which
    makes `Compared` a data protocol, and Python refuses `issubclass` on those
    outright. `isinstance` would work and needs an instance -- which these
    eighteen types cannot be given generically, since each takes the results of
    a real run. So the type is asked for the property directly, which is the
    same question one level down.
    """
    compared = getattr(declaration.comparison, "compared", None)

    assert isinstance(compared, property), (
        f"{declaration.module}.{declaration.comparison.__name__} cannot be asked what it compared"
    )


@pytest.mark.trace("REQ-BIAS-011")
def test_no_two_modules_claim_the_same_experiment() -> None:
    """Two modules under one id would write into one field, and a reader could
    not tell which experiment discarded what."""
    ids = [d.experiment for d in declarations()]

    assert len(set(ids)) == len(ids), sorted(ids)


@pytest.mark.trace("REQ-BIAS-011")
def test_an_experiment_id_is_not_empty() -> None:
    """`Run` refuses an unnamed experiment, and finding that out at the registry
    is finding it out too late."""
    for declaration in declarations():
        assert declaration.experiment.strip(), declaration.module


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_type_is_what_the_seam_expects() -> None:
    """A `compared` returning something else would satisfy the protocol and fail
    at the registry, which is the failure this file exists to move earlier."""
    for declaration in declarations():
        annotation = declaration.comparison.compared.fget.__annotations__["return"]
        assert annotation in (Field, "Field"), (declaration.module, annotation)


@pytest.mark.trace("REQ-BIAS-011")
def test_a_real_comparison_reaches_the_registry() -> None:
    """The whole chain on one real experiment, end to end.

    The checks above are structural: they prove a comparison *can* be asked what
    it compared. This one runs EXP-001 for real, pushes the answer through the
    seam, and reads the registry back -- because a `compared` property that
    returns an empty field would satisfy every structural check and fail the
    moment anyone used it.
    """
    from channelflow.experiments import CodeVersion, Outcome, Registry, report_comparison
    from channelflow.lakehouse import InMemoryObjectStore
    from channelflow.research import MODELS, compare_channel_models
    from tests.unit.research.test_channel_comparison import COSTS, series

    comparison = compare_channel_models(series(), costs=COSTS)
    registry = Registry(store=InMemoryObjectStore())

    result = report_comparison(
        comparison,
        experiment=channelflow.research.channel_comparison.EXPERIMENT,
        dataset="d" * 64,
        code=CodeVersion(commit="a" * 40, dirty=False),
        registry=registry,
        as_of_ns=1,
    )

    assert result.recorded == len(MODELS)
    assert {run.variant for run in registry.runs()} == set(MODELS)
    # EXP-001 ranks nothing, so every variant is on record and none is kept.
    assert result.report is None
    assert all(run.outcome is Outcome.DISCARDED for run in registry.runs())
    # The five models are five distinct runs: same dataset, same code, so the
    # config is the only thing that can tell them apart.
    assert len(registry.hashes()) == len(MODELS)
