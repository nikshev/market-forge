"""PRD §0 item 13's four components (REQ-REPRO-001)."""

from __future__ import annotations

import pytest

from channelflow.experiments import (
    CodeVersion,
    ModelAbsence,
    NotReproducible,
    RunIdentity,
    why_not,
)

from .conftest import COMMIT, OTHER_COMMIT, dataset, identity


@pytest.mark.trace("REQ-REPRO-001")
def test_a_run_with_all_four_components_is_reproducible() -> None:
    """The control: without it, every refusal below would be consistent with a
    gate that refuses everything."""
    run = identity(model="d" * 64)

    assert run.reproducible
    assert run.missing == ()
    assert why_not(run) == ""


@pytest.mark.trace("REQ-REPRO-001")
def test_a_run_that_fits_no_model_is_still_reproducible() -> None:
    """A statistical comparison has no artifact and was never going to have one.
    Requiring a hash here would force a fake, and a fake in a reproducibility
    record is worse than a blank."""
    run = identity(model=ModelAbsence.NO_MODEL)

    assert run.reproducible


@pytest.mark.trace("REQ-REPRO-001")
def test_a_model_whose_artifact_nobody_recorded_is_not_reproducible() -> None:
    """The opposite of the case above, and the reason both are spelled out: a
    blank field cannot tell them apart, and one of them is fine."""
    run = identity(model=ModelAbsence.UNRECORDED)

    assert not run.reproducible
    assert any("model artifact" in gap for gap in run.missing)
    with pytest.raises(NotReproducible, match="model artifact"):
        run.require_reproducible()


@pytest.mark.trace("REQ-REPRO-001")
def test_a_commit_from_a_dirty_tree_is_not_reproducible() -> None:
    """`git rev-parse HEAD` answers cheerfully in a tree with uncommitted
    changes, and the answer names a tree that never ran. That is the
    unreproducible case which looks most convincing: the hash resolves, the
    commit exists, the diff is gone."""
    run = identity(dirty=True)

    assert not run.reproducible
    assert any("uncommitted" in gap for gap in run.missing)


@pytest.mark.trace("REQ-REPRO-001")
def test_every_missing_component_is_named_at_once() -> None:
    """Not the first. A caller who fixes one and re-runs should not discover the
    next one the same way."""
    run = identity(dirty=True, model=ModelAbsence.UNRECORDED)

    assert len(run.missing) == 2


@pytest.mark.trace("REQ-REPRO-001")
def test_an_abbreviated_or_invented_commit_is_refused() -> None:
    """Recording a commit is for resolving it later, and a short hash cannot be
    resolved without the repository it came from."""
    for bad in ("abc1234", "", "z" * 40, "A" * 40):
        with pytest.raises(ValueError, match="commit hash"):
            CodeVersion(commit=bad, dirty=False)


@pytest.mark.trace("REQ-REPRO-001")
def test_a_run_with_no_dataset_or_no_config_is_refused_outright() -> None:
    """Not merely marked unreproducible: an empty string here would record that
    a run can be replayed from nothing."""
    with pytest.raises(ValueError, match="dataset"):
        RunIdentity(
            dataset="",
            config="x",
            code=CodeVersion(commit=COMMIT, dirty=False),
            model_artifact=ModelAbsence.NO_MODEL,
        )
    with pytest.raises(ValueError, match="config"):
        RunIdentity(
            dataset="x",
            config="",
            code=CodeVersion(commit=COMMIT, dirty=False),
            model_artifact=ModelAbsence.NO_MODEL,
        )


@pytest.mark.trace("REQ-REPRO-001")
def test_the_same_four_components_give_the_same_run_hash() -> None:
    assert identity().run_hash == identity().run_hash


@pytest.mark.trace("REQ-REPRO-001")
def test_changing_any_component_changes_the_run_hash() -> None:
    base = identity().run_hash

    assert identity(data=dataset(snapshot=2)).run_hash != base
    assert identity(config={"lookback": 61}).run_hash != base
    assert identity(commit=OTHER_COMMIT).run_hash != base
    assert identity(model="d" * 64).run_hash != base


@pytest.mark.trace("REQ-REPRO-001")
def test_a_dirty_run_is_not_the_same_run_as_its_commit() -> None:
    """Same commit, different tree. One identity for both would let the dirty
    result silently stand in for the clean one."""
    assert identity(dirty=True).run_hash != identity(dirty=False).run_hash


@pytest.mark.trace("REQ-REPRO-001")
def test_a_component_cannot_borrow_a_character_from_the_next_one() -> None:
    """Length-prefixed, not concatenated.

    Concatenated, a run over dataset `ab` with config `c` hashes identically to
    one over dataset `a` with config `bc` -- two different runs sharing an
    identity, and the two that would collide in practice are a dataset hash and
    a config hash whose boundary moved by one character.
    """
    left = RunIdentity(
        dataset="ab",
        config="c",
        code=CodeVersion(commit=COMMIT, dirty=False),
        model_artifact=ModelAbsence.NO_MODEL,
    )
    right = RunIdentity(
        dataset="a",
        config="bc",
        code=CodeVersion(commit=COMMIT, dirty=False),
        model_artifact=ModelAbsence.NO_MODEL,
    )

    assert left.run_hash != right.run_hash
