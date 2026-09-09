"""The reporting gate (REQ-REPRO-001, REQ-BIAS-011).

PRD §0 item 13 and PRD §41 rule 11 meet here, and neither is enforceable by
storing a field.
"""

from __future__ import annotations

import pytest

from channelflow.experiments import (
    CherryPicked,
    ModelAbsence,
    NotReproducible,
    Outcome,
    Registry,
    Run,
    publish,
)

from .conftest import SECOND, identity


def variant(name: str) -> tuple[str, object]:
    return name, identity(config={"variant": name})


def record(registry: Registry, *names: str) -> None:
    registry.record(
        [
            Run(
                experiment="EXP-001",
                variant=name,
                identity=identity(config={"variant": name}),
                outcome=Outcome.DISCARDED,
                as_of_ns=SECOND,
            )
            for name in names
        ]
    )


@pytest.mark.trace("REQ-REPRO-001")
def test_a_reproducible_winner_with_its_whole_field_on_record_is_published(
    registry: Registry,
) -> None:
    """The control. Without it every refusal below would be consistent with a
    gate that refuses everything."""
    record(registry, "quantile", "kalman", "huber")

    report = publish(
        experiment="EXP-001",
        winner="quantile",
        identity=identity(config={"variant": "quantile"}),
        considered=[variant("quantile"), variant("kalman"), variant("huber")],  # type: ignore[list-item]
        registry=registry,
    )

    assert report.winner == "quantile"
    assert report.field == ("quantile", "kalman", "huber")
    assert "3 variant(s)" in report.summary


@pytest.mark.trace("REQ-REPRO-001")
def test_an_irreproducible_result_cannot_be_reported(registry: Registry) -> None:
    """A record that merely stores four fields satisfies nothing: the commit can
    come from a dirty tree and the result gets published anyway. The gate is what
    makes PRD §0 item 13 a rule rather than a field."""
    record(registry, "quantile")

    with pytest.raises(NotReproducible, match="uncommitted"):
        publish(
            experiment="EXP-001",
            winner="quantile",
            identity=identity(config={"variant": "quantile"}, dirty=True),
            considered=[variant("quantile")],  # type: ignore[list-item]
            registry=registry,
        )


@pytest.mark.trace("REQ-REPRO-001")
def test_an_unrecorded_model_artifact_stops_a_report_too(registry: Registry) -> None:
    record(registry, "gmdh")

    with pytest.raises(NotReproducible, match="model artifact"):
        publish(
            experiment="EXP-001",
            winner="gmdh",
            identity=identity(config={"variant": "gmdh"}, model=ModelAbsence.UNRECORDED),
            considered=[variant("gmdh")],  # type: ignore[list-item]
            registry=registry,
        )


@pytest.mark.trace("REQ-BIAS-011")
def test_a_variant_that_lost_and_was_never_recorded_stops_the_report(
    registry: Registry,
) -> None:
    """PRD §41 rule 11's actual target: the variant that was run, lost, and
    quietly dropped.

    Storing is not checkable -- nobody can know what was considered and never
    written down. What is checkable is that every name in the field the winner
    is claimed to have won is already on record.
    """
    record(registry, "quantile")

    with pytest.raises(CherryPicked, match="kalman"):
        publish(
            experiment="EXP-001",
            winner="quantile",
            identity=identity(config={"variant": "quantile"}),
            considered=[variant("quantile"), variant("kalman")],  # type: ignore[list-item]
            registry=registry,
        )


@pytest.mark.trace("REQ-BIAS-011")
def test_a_winner_that_is_not_in_its_own_field_is_refused(registry: Registry) -> None:
    """A result chosen from a set it was not in is not a choice anyone can
    check."""
    record(registry, "kalman")

    with pytest.raises(CherryPicked, match="not among"):
        publish(
            experiment="EXP-001",
            winner="quantile",
            identity=identity(config={"variant": "quantile"}),
            considered=[variant("kalman")],  # type: ignore[list-item]
            registry=registry,
        )


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_that_counts_a_variant_twice_is_refused(registry: Registry) -> None:
    """One variant counted twice makes the field look wider than it was, which
    is the number a reader uses to judge how much searching went on."""
    record(registry, "quantile")

    with pytest.raises(CherryPicked, match="appears twice"):
        publish(
            experiment="EXP-001",
            winner="quantile",
            identity=identity(config={"variant": "quantile"}),
            considered=[variant("quantile"), variant("quantile")],  # type: ignore[list-item]
            registry=registry,
        )


@pytest.mark.trace("REQ-BIAS-011")
def test_a_field_of_one_is_a_legitimate_report(registry: Registry) -> None:
    """Of a study that compared nothing. The gate is about the field being on
    record, not about it being wide."""
    record(registry, "only")

    report = publish(
        experiment="EXP-001",
        winner="only",
        identity=identity(config={"variant": "only"}),
        considered=[variant("only")],  # type: ignore[list-item]
        registry=registry,
    )

    assert report.field == ("only",)


@pytest.mark.trace("REQ-REPRO-001")
def test_a_report_carries_the_three_hashes_a_reader_needs(registry: Registry) -> None:
    """The dataset, the config and the commit, so the claim can be checked
    without going back to whoever made it."""
    record(registry, "quantile")
    run = identity(config={"variant": "quantile"})

    report = publish(
        experiment="EXP-001",
        winner="quantile",
        identity=run,
        considered=[variant("quantile")],  # type: ignore[list-item]
        registry=registry,
    )

    assert report.dataset == run.dataset
    assert report.config == run.config
    assert report.code_commit == run.code.commit
    assert report.winner_hash == run.run_hash
