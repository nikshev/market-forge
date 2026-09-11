"""A registration names the dataset it was trained on (REQ-WP-040).

PRD §0 item 13 asks a result to be reproducible from four things. Three were
recorded. This is the fourth, and its absence was silent: a run with no dataset
looked like every other run, and `require_registered` passed it.
"""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.models.registry import (
    DatasetOrigin,
    NoDataset,
    Resolution,
    pins_for,
    resolve,
)

SECOND = 1_000_000_000


def schema() -> Schema:
    return Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="v", type="float64"),
        ),
        event_time_column="event_time_ns",
    )


def row(index: int) -> dict[str, object]:
    return {"event_time_ns": index * SECOND, "v": float(index)}


def filled(catalog: Catalog, commits: int = 3) -> IcebergTable:
    table = IcebergTable(name="features", schema=schema(), catalog=catalog)
    for index in range(commits):
        table.append([row(index)])
    return table


# --- a result names its data --------------------------------------------------


@pytest.mark.trace("REQ-WP-040")
def test_an_origin_carries_the_table_the_snapshot_and_the_hash(catalog: Catalog) -> None:
    table = filled(catalog)

    origin = DatasetOrigin.of(table)

    assert origin.table == "features"
    assert origin.snapshot_id == table.snapshot_ids()[-1]
    assert origin.content_hash == table.current().content_hash


@pytest.mark.trace("REQ-WP-040")
def test_an_origin_can_name_an_earlier_snapshot(catalog: Catalog) -> None:
    """Whoever read the table knows which snapshot they read."""
    table = filled(catalog)

    origin = DatasetOrigin.of(table, snapshot_id=1)

    assert origin.snapshot_id == 1
    assert origin.content_hash == table.snapshot(1).content_hash


@pytest.mark.trace("REQ-WP-040")
def test_the_same_rows_give_the_same_citation(catalog: Catalog, tmp_path: object) -> None:
    """Identity is the rows ([[ADR-053]]), so two planes holding the same data
    produce the same claim about it."""
    from pathlib import Path

    from channelflow.lakehouse import catalog as open_catalog

    other = Path(str(tmp_path)) / "elsewhere"
    other.mkdir()
    elsewhere = open_catalog(uri=f"sqlite:///{other}/catalog.db", warehouse=str(other))

    here = DatasetOrigin.of(filled(catalog))
    there = DatasetOrigin.of(filled(elsewhere))

    assert here.content_hash == there.content_hash


@pytest.mark.trace("REQ-WP-040")
def test_a_registration_without_a_dataset_is_refused() -> None:
    """[[ADR-015]]: a field with a default is a field an author can forget to
    think about, and this one selects whether a result is checkable."""
    from channelflow.models.registry import Registration

    with pytest.raises(TypeError):
        Registration(  # type: ignore[call-arg]
            model_type="baseline",
            feature_set_versions={"a": 1},
            train_start_ns=0,
            train_end_ns=1,
            validation_start_ns=2,
            validation_end_ns=3,
            code_commit="abc",
            hyperparameters={"k": 1},
            scaler_parameters={},
            calibration_model="none",
            metrics={"auc": 0.5},
            artifact_hash="h",
            deployment_status="shadow",
        )


@pytest.mark.trace("REQ-WP-040")
def test_an_origin_with_no_table_is_refused(catalog: Catalog) -> None:
    """A citation of "some of it" is not a citation."""
    with pytest.raises(NoDataset):
        DatasetOrigin(table="", snapshot_id=1, content_hash="h")


# --- a vanished dataset is visible --------------------------------------------


@pytest.mark.trace("REQ-WP-040")
def test_a_dataset_that_is_still_there_resolves(catalog: Catalog) -> None:
    table = filled(catalog)

    assert resolve(DatasetOrigin.of(table), table) is Resolution.RESOLVED


@pytest.mark.trace("REQ-WP-040")
def test_a_snapshot_that_now_holds_something_else_is_not_the_same_dataset(
    catalog: Catalog,
) -> None:
    """The case a citation exists to catch, and the one a check on the id alone
    would pass: the name still resolves and the rows are different."""
    table = filled(catalog)
    origin = DatasetOrigin.of(table)
    forged = DatasetOrigin(
        table=origin.table, snapshot_id=origin.snapshot_id, content_hash="0" * 64
    )

    assert resolve(forged, table) is Resolution.CHANGED


@pytest.mark.trace("REQ-WP-040")
def test_a_snapshot_retention_expired_resolves_as_gone(catalog: Catalog) -> None:
    from channelflow.lakehouse.retention import RetentionPolicy
    from channelflow.lakehouse.retention import apply as prune

    table = filled(catalog, commits=4)
    origin = DatasetOrigin.of(table, snapshot_id=1)

    prune(table, policy=RetentionPolicy(keep_ns=0), now_ns=10_000 * SECOND)

    assert resolve(origin, table) is Resolution.GONE


@pytest.mark.trace("REQ-WP-040")
def test_an_unresolvable_dataset_does_not_stop_the_registration_being_read(
    catalog: Catalog,
) -> None:
    """The run happened. Refusing to read the record of it would make every
    report unreadable after a legitimate retention pass."""
    table = filled(catalog)
    origin = DatasetOrigin(table="features", snapshot_id=99, content_hash="h")

    assert resolve(origin, table) is Resolution.GONE
    assert origin.table == "features"


# --- retention reads the lineage ----------------------------------------------


@pytest.mark.trace("REQ-WP-040")
def test_pins_are_the_snapshots_registrations_name(catalog: Catalog, registry) -> None:
    """What [[REQ-WP-038]] left open: retention keeps the snapshots a lineage
    names, and there was no lineage to read."""
    table = filled(catalog, commits=4)
    registry.record(
        [
            _registration(DatasetOrigin.of(table, snapshot_id=1), "a"),
            _registration(DatasetOrigin.of(table, snapshot_id=3), "b"),
        ]
    )

    assert pins_for(registry, "features") == (1, 3)


@pytest.mark.trace("REQ-WP-040")
def test_two_registrations_over_one_snapshot_are_one_pin(catalog: Catalog, registry) -> None:
    table = filled(catalog, commits=2)
    origin = DatasetOrigin.of(table, snapshot_id=1)
    registry.record([_registration(origin, "a"), _registration(origin, "b")])

    assert pins_for(registry, "features") == (1,)


@pytest.mark.trace("REQ-WP-040")
def test_a_registry_holding_nothing_for_a_table_pins_nothing(catalog: Catalog, registry) -> None:
    """Empty, and a caller can tell it from not having asked: "no lineage to
    protect" and "I forgot to look" produce the same prune otherwise."""
    filled(catalog)

    assert pins_for(registry, "features") == ()


@pytest.mark.trace("REQ-WP-040")
def test_a_registered_snapshot_survives_a_pass_that_would_have_expired_it(
    catalog: Catalog, registry
) -> None:
    from channelflow.lakehouse.retention import RetentionPolicy
    from channelflow.lakehouse.retention import apply as prune

    table = filled(catalog, commits=4)
    registry.record([_registration(DatasetOrigin.of(table, snapshot_id=2), "a")])

    prune(
        table,
        policy=RetentionPolicy(keep_ns=0),
        now_ns=10_000 * SECOND,
        pinned=pins_for(registry, "features"),
    )

    assert 2 in table.snapshot_ids()


def _registration(origin: DatasetOrigin, variant: str):
    from channelflow.models.registry import Registration

    return Registration(
        model_type=variant,
        feature_set_versions={"a": 1},
        train_start_ns=0,
        train_end_ns=1,
        validation_start_ns=2,
        validation_end_ns=3,
        code_commit="abc1234",
        hyperparameters={"k": 1},
        scaler_parameters={},
        calibration_model="none",
        metrics={"auc": 0.5},
        artifact_hash=f"hash-{variant}",
        deployment_status="shadow",
        validation_regime="single_split",
        dataset=origin,
    )


@pytest.mark.trace("REQ-WP-040")
def test_a_citation_by_name_without_a_claim_is_refused() -> None:
    """A snapshot id is a name. Without the hash there is nothing to check it
    against, and the citation would pass every test forever."""
    with pytest.raises(NoDataset):
        DatasetOrigin(table="features", snapshot_id=1, content_hash="")


@pytest.mark.trace("REQ-WP-040")
def test_pins_for_one_table_are_not_pins_for_another(catalog: Catalog, registry) -> None:
    """Two tables, two lineages. Pinning one table's snapshots while pruning
    another would keep the wrong history alive and let the right one go."""
    features = filled(catalog, commits=3)
    bars = IcebergTable(name="bars", schema=schema(), catalog=catalog)
    for index in range(3):
        bars.append([row(index)])

    registry.record(
        [
            _registration(DatasetOrigin.of(features, snapshot_id=1), "a"),
            _registration(DatasetOrigin.of(bars, snapshot_id=3), "b"),
        ]
    )

    assert pins_for(registry, "features") == (1,)
    assert pins_for(registry, "bars") == (3,)
