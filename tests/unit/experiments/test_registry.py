"""The registry, and PRD §41 rule 11 (REQ-REPRO-001, REQ-BIAS-011)."""

from __future__ import annotations

import pytest

from channelflow.experiments import (
    SCHEMA,
    TABLE_NAME,
    ModelAbsence,
    Outcome,
    Registry,
    Run,
)

from .conftest import SECOND, identity


def run(
    variant: str,
    *,
    outcome: Outcome = Outcome.DISCARDED,
    experiment: str = "EXP-001",
    **kwargs: object,
) -> Run:
    return Run(
        experiment=experiment,
        variant=variant,
        identity=identity(config={"variant": variant}, **kwargs),  # type: ignore[arg-type]
        outcome=outcome,
        as_of_ns=10 * SECOND,
    )


@pytest.mark.trace("REQ-BIAS-011")
def test_a_discarded_variant_is_recorded_exactly_like_a_kept_one(registry: Registry) -> None:
    """PRD §41 rule 11 in one assertion. The registry that only holds winners is
    the registry the rule is against."""
    registry.record(
        [
            run("quantile", outcome=Outcome.KEPT),
            run("kalman", outcome=Outcome.DISCARDED),
            run("huber", outcome=Outcome.DISCARDED),
        ]
    )

    recorded = registry.runs()

    assert len(recorded) == 3
    assert {r.variant for r in recorded} == {"quantile", "kalman", "huber"}
    assert {r.outcome for r in recorded} == {Outcome.KEPT, Outcome.DISCARDED}


@pytest.mark.trace("REQ-REPRO-001")
def test_an_unreproducible_run_is_recorded_rather_than_refused(registry: Registry) -> None:
    """Refusing it would leave no trace of it at all, which is the outcome
    PRD §41 rule 11 exists to prevent. It is recorded, and recorded as
    unreproducible, with the reason in the row."""
    registry.record([run("dirty_tree", dirty=True)])

    recorded = registry.runs()[0]

    assert not recorded.reproducible
    assert "uncommitted" in recorded.note


@pytest.mark.trace("REQ-REPRO-001")
def test_a_recorded_run_reads_back_with_its_identity_intact(registry: Registry) -> None:
    original = run("quantile", outcome=Outcome.KEPT, model="d" * 64)
    registry.record([original])

    recorded = registry.runs()[0]

    assert recorded.run_hash == original.identity.run_hash
    assert recorded.experiment == "EXP-001"
    assert recorded.outcome is Outcome.KEPT
    assert recorded.reproducible


@pytest.mark.trace("REQ-REPRO-001")
def test_an_absence_reads_back_as_an_absence(registry: Registry) -> None:
    """Not as a string that happens to read like one: a caller comparing against
    `ModelAbsence.NO_MODEL` should get the answer rather than a near miss."""
    registry.record(
        [
            run("no_model", model=ModelAbsence.NO_MODEL),
            run("unrecorded", model=ModelAbsence.UNRECORDED),
            run("hashed", model="d" * 64),
        ]
    )

    by_variant = {r.variant: r.model_artifact for r in registry.runs()}

    assert by_variant["no_model"] is ModelAbsence.NO_MODEL
    assert by_variant["unrecorded"] is ModelAbsence.UNRECORDED
    assert by_variant["hashed"] == "d" * 64


@pytest.mark.trace("REQ-BIAS-011")
def test_the_registry_is_append_only_and_its_history_does_not_change(
    registry: Registry,
) -> None:
    """A registry that could be tidied up after the fact would defeat the rule it
    exists to enforce. It is a lakehouse table, so this is the storage layer's
    guarantee rather than a new one."""
    first = registry.record([run("a")])
    registry.record([run("b")])

    assert registry.table.snapshot(1).content_hash == first
    assert registry.table.read(snapshot_id=1).num_rows == 1
    assert len(registry.runs()) == 2


@pytest.mark.trace("REQ-REPRO-001")
def test_recording_nothing_is_refused(registry: Registry) -> None:
    with pytest.raises(ValueError, match="says nothing"):
        registry.record([])


@pytest.mark.trace("REQ-REPRO-001")
def test_a_run_without_a_variant_name_is_refused() -> None:
    """An unnamed variant cannot be told apart from the others it was chosen
    against, which is the whole content of a field."""
    with pytest.raises(ValueError, match="names an experiment and a variant"):
        Run(
            experiment="EXP-001",
            variant="",
            identity=identity(),
            outcome=Outcome.KEPT,
            as_of_ns=SECOND,
        )


@pytest.mark.trace("REQ-REPRO-001")
def test_the_registry_table_can_answer_a_point_in_time_read(registry: Registry) -> None:
    """Its event-time column is the experiment's own as-of instant, not a clock
    reading -- so the registry is a table on the plane like any other, and two
    replays of one study produce identical rows."""
    assert SCHEMA.event_time_column == "event_time_ns"
    assert registry.table.name == TABLE_NAME

    registry.record([run("a")])

    assert registry.table.read(as_of_ns=10 * SECOND).num_rows == 1
    assert registry.table.read(as_of_ns=10 * SECOND - 1).num_rows == 0


@pytest.mark.trace("REQ-REPRO-001")
def test_nothing_in_the_experiments_package_consults_a_clock() -> None:
    """A registry stamped with wall-clock time would make two replays of one
    study produce different rows, and the registry's own content hash would
    change for a run that did not."""
    from pathlib import Path

    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "experiments"
    modules = sorted(package.glob("*.py"))
    assert modules, "the experiments package has no modules; this test would pass vacuously"
    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


@pytest.mark.trace("REQ-REPRO-001")
def test_nothing_in_the_experiments_package_shells_out_to_git() -> None:
    """The commit and the dirty flag are supplied by the caller.

    A library that runs `git rev-parse` cannot be tested, behaves differently
    inside a container, and answers about whatever directory it happens to be
    in rather than about the code that ran.
    """
    from pathlib import Path

    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "experiments"
    for module in sorted(package.glob("*.py")):
        source = module.read_text()
        for forbidden in ("subprocess", "os.system", "sh.git", '"git"', "'git'"):
            assert forbidden not in source, f"{module.name} reaches for git: {forbidden!r}"
