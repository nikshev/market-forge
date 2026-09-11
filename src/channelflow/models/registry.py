"""What a fitted model is, as a value, and the record that describes it.

# @trace: REQ-WP-022
# @trace: REQ-WP-040

PRD §0 item 13 wants four hashes behind every research result.
[[REQ-REPRO-001]] built all four components and three of them have producers.
This is the fourth: before it, `ModelArtifact` appeared nowhere outside
`channelflow.experiments`, so every run that fitted a model recorded
`UNRECORDED` -- the value whose entire job is to say the run cannot be repeated.

PRD §23.9 names eleven fields, and one of them is the artifact hash. That
settles what the hash is *of*: the model, not the registration describing it.

**The hash covers what was learned and how it was told to learn.** Two models
that landed on identical weights from different penalties are not one artifact;
one of them behaves differently on the next dataset, and a hash merging them
would certify a reproduction that is not one.

**Exact bytes.** Two fits differing in the last bit produce different
probabilities, so they are different models. A hash that rounded them together
would lie about the one thing it exists to certify. A platform that produces
different bytes has produced a different artifact, and saying so is more honest
than hiding it.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast, get_args

import numpy as np

from channelflow.experiments import ModelAbsence, NotReproducible, RunIdentity
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

_TAG_NONE = b"n"
_TAG_BOOL = b"b"
_TAG_INT = b"i"
_TAG_FLOAT = b"f"
_TAG_STR = b"s"
_TAG_BYTES = b"y"
_TAG_SEQ = b"q"
_TAG_MAP = b"m"
_TAG_ARRAY = b"a"
_TAG_OBJECT = b"o"


#: PRD §23.9's four span fields describe a run, and what they can say depends on
#: how it was validated.
#:
#: **`single_split`** trains on one range and validates on a later one, so the
#: spans are the whole of what happened and an overlap between them is a leak.
#:
#: **`walk_forward`** interleaves by construction: fold 1 trains on data later
#: than fold 0 validated on. Within a fold the two never touch, and that is the
#: property that matters -- enforced by the fold builder and checked by the
#: leakage certificate, which is where a real guarantee lives. A run-level span
#: pair for such a run overlaps and is not a leak.
#:
#: This distinction is a correction. The first version of this rule refused any
#: overlap and cited PRD §41 rule 10 for it. §23.9 asks for no such thing, rule
#: 10 is about a locked test segment which walk-forward satisfies per fold, and
#: the strict form duplicated a guarantee that already existed -- with a cruder
#: test that a correct scheme legitimately fails. See [[ADR-058]].
ValidationRegime = Literal["single_split", "walk_forward"]

VALIDATION_REGIMES: tuple[str, ...] = get_args(ValidationRegime)


class ModelNotFitted(ValueError):
    """An artifact hash was asked for a model that has learned nothing."""


def artifact_hash(model: object) -> str:
    """A hash of everything a fitted model is.

    Refused for an unfitted one rather than returned: a hash of an unfitted
    model is a stable, meaningless string that every unfitted model of that type
    shares, and it would certify runs that never happened.
    """
    if not getattr(model, "fitted", False):
        name = getattr(model, "name", type(model).__name__)
        raise ModelNotFitted(
            f"{name} has not been fitted, so it has no artifact to hash; a hash of an "
            "unfitted model would be shared by every unfitted model of its type"
        )
    digest = hashlib.sha256()
    _absorb(digest, model)
    return digest.hexdigest()


def _absorb(digest: hashlib._Hash, value: object) -> None:
    """Feed `value` into `digest`, framed.

    Framed the way [[REQ-REPRO-001]]'s run hash is: every part is preceded by
    its tag and its length, so no field can borrow a character from the next and
    two different models cannot concatenate to one string.
    """
    if value is None:
        digest.update(_TAG_NONE)
    elif isinstance(value, bool):
        digest.update(_TAG_BOOL + (b"\x01" if value else b"\x00"))
    elif isinstance(value, int):
        _part(digest, _TAG_INT, str(value).encode())
    elif isinstance(value, float):
        # The bit pattern, not the repr. Two floats that print alike and differ
        # in the last bit are two different models.
        _part(digest, _TAG_FLOAT, struct.pack("<d", value))
    elif isinstance(value, str):
        _part(digest, _TAG_STR, value.encode())
    elif isinstance(value, bytes | bytearray):
        _part(digest, _TAG_BYTES, bytes(value))
    elif isinstance(value, np.ndarray):
        # dtype and shape as well as the bytes: the same buffer read as float32
        # or reshaped is a different array and a different model.
        _part(digest, _TAG_ARRAY, str(value.dtype).encode())
        _part(digest, _TAG_ARRAY, str(value.shape).encode())
        _part(digest, _TAG_ARRAY, value.tobytes())
    elif isinstance(value, Mapping):
        digest.update(_TAG_MAP)
        _part(digest, _TAG_MAP, str(len(value)).encode())
        # Sorted, so a mapping built in a different order is the same mapping.
        for key in sorted(value, key=str):
            _absorb(digest, str(key))
            _absorb(digest, value[key])
    elif isinstance(value, list | tuple):
        digest.update(_TAG_SEQ)
        _part(digest, _TAG_SEQ, str(len(value)).encode())
        for item in value:
            _absorb(digest, item)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        digest.update(_TAG_OBJECT)
        _part(digest, _TAG_OBJECT, type(value).__name__.encode())
        for spec in dataclasses.fields(value):
            _absorb(digest, spec.name)
            _absorb(digest, getattr(value, spec.name))
    else:
        raise ModelNotFitted(
            f"a {type(value).__name__} is in this model's state and has no canonical "
            "encoding; hashing its repr would put a memory address in the artifact hash"
        )


def _part(digest: hashlib._Hash, tag: bytes, raw: bytes) -> None:
    digest.update(tag)
    digest.update(struct.pack("<I", len(raw)))
    digest.update(raw)


class NoDataset(ValueError):
    """A citation that does not name a dataset.

    PRD §0 item 13 asks a result to be reproducible from "a versioned dataset +
    config + code commit hash + model artifact hash". A citation of "some of it"
    is not a citation.
    """


class Resolution(StrEnum):
    """What became of a cited dataset.

    Three, not two. A check that only asked whether the snapshot id still exists
    would pass `CHANGED` -- a name that resolves over different rows -- which is
    precisely the case a citation exists to catch. An id is a name and a hash is
    a claim about what was under it ([[ADR-053]]).
    """

    RESOLVED = "resolved"
    CHANGED = "changed"
    GONE = "gone"


@dataclass(frozen=True)
class DatasetOrigin:
    """Which table, which snapshot, and what was under it.

    Built from the table so the hash is the one the plane computed, and
    **supplied rather than inferred** everywhere after that: a layer that
    re-derived it would ask the table what it holds *now*, which is the right
    answer to a different question and wrong exactly when the table has moved
    on -- the case the citation is for.
    """

    table: str
    snapshot_id: int
    content_hash: str

    def __post_init__(self) -> None:
        if not self.table.strip():
            raise NoDataset("a citation with no table names nothing")
        if not self.content_hash.strip():
            raise NoDataset(
                f"{self.table} snapshot {self.snapshot_id} is cited by name and not by "
                "content; a name without a claim cannot be checked"
            )

    @classmethod
    def of(cls, table: object, snapshot_id: int | None = None) -> DatasetOrigin:
        snapshot = table.current() if snapshot_id is None else table.snapshot(snapshot_id)  # type: ignore[attr-defined]
        if snapshot is None:
            raise NoDataset(f"{table.name} has no snapshot to cite")  # type: ignore[attr-defined]
        return cls(
            table=table.name,  # type: ignore[attr-defined]
            snapshot_id=snapshot.snapshot_id,
            content_hash=snapshot.content_hash,
        )


def resolve(origin: DatasetOrigin, table: object) -> Resolution:
    """Whether a citation still means what it meant.

    `GONE` is not an error: a registration whose dataset has been expired still
    records a run that happened, and refusing to read it would make every report
    unreadable after a legitimate retention pass.
    """
    if origin.snapshot_id not in table.snapshot_ids():  # type: ignore[attr-defined]
        return Resolution.GONE
    found = table.snapshot(origin.snapshot_id)  # type: ignore[attr-defined]
    return Resolution.RESOLVED if found.content_hash == origin.content_hash else Resolution.CHANGED


def pins_for(registry: ModelRegistry, table: str) -> tuple[int, ...]:
    """The snapshots this registry's registrations name for one table.

    What [[REQ-WP-038]] left open. An empty tuple is an answer -- "no lineage to
    protect" and "nobody looked" produce the same prune otherwise.
    """
    return tuple(
        sorted(
            {
                entry.dataset.snapshot_id
                for entry in registry.entries()
                if entry.dataset.table == table
            }
        )
    )


@dataclass(frozen=True)
class Registration:
    """PRD §23.9's eleven fields about one artifact."""

    model_type: str
    feature_set_versions: Mapping[str, int]
    train_start_ns: int
    train_end_ns: int
    validation_start_ns: int
    validation_end_ns: int
    code_commit: str
    hyperparameters: Mapping[str, object]
    scaler_parameters: Mapping[str, object]
    calibration_model: str
    metrics: Mapping[str, float]
    artifact_hash: str
    deployment_status: str
    #: How the run was validated, which decides what the four span fields can
    #: say. No default, for [[ADR-015]]'s reason: a field with one is a field an
    #: author can forget to think about, and this one selects a rule.
    validation_regime: ValidationRegime
    #: Which dataset this was trained on ([[REQ-WP-040]]). No default: PRD §0
    #: item 13 needs it and [[ADR-015]] says a field with a default is a field
    #: an author can forget to think about.
    dataset: DatasetOrigin

    def __post_init__(self) -> None:
        for name in (
            "model_type",
            "code_commit",
            "calibration_model",
            "artifact_hash",
            "deployment_status",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(
                    f"{name} is empty; PRD section 23.9 names it, and a registration "
                    "missing it describes an artifact nobody could identify"
                )
        for name in ("feature_set_versions", "hyperparameters", "metrics"):
            if not getattr(self, name):
                raise ValueError(
                    f"{name} is empty; a model registered with no {name.replace('_', ' ')} "
                    "was not evaluated, and PRD section 45's Phase 7 acceptance turns on "
                    "measurements"
                )
        for span in ("train", "validation"):
            start = getattr(self, f"{span}_start_ns")
            end = getattr(self, f"{span}_end_ns")
            if end <= start:
                raise ValueError(
                    f"the {span} span ends at {end} and starts at {start}; a span that "
                    "ends before it starts contains no rows"
                )
        if self.validation_regime not in VALIDATION_REGIMES:
            raise ValueError(
                f"validation_regime {self.validation_regime!r} is not one of "
                f"{VALIDATION_REGIMES}; the four span fields mean different things under "
                "each, so a registration that does not say which is not readable"
            )
        if (
            self.validation_regime == "single_split"
            and self.validation_start_ns < self.train_end_ns
        ):
            raise ValueError(
                f"the training span ends at {self.train_end_ns} and validation starts at "
                f"{self.validation_start_ns}, so they overlap; for a single split the spans "
                "are the whole of what happened, so an overlap between them is the leak "
                "itself, and PRD section 41 rule 10 exists to stop the number that comes out"
            )


MODEL_REGISTRY_TABLE = "model_registry"

#: PRD §29.B lists the registry among the tables the plane holds, and [[ADR-002]]
#: made object storage canonical. A registry that could be edited after the fact
#: would defeat what it exists for -- the same argument [[ADR-054]] made for the
#: experiment registry, and the same answer.
#:
#: The three mappings are JSON strings rather than typed columns because their
#: keys are the caller's: a feature set nobody has invented yet must not need a
#: schema change, which would change the fingerprint of every dataset citing
#: this table.
MODEL_REGISTRY_SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="artifact_hash", type="string"),
        Column(name="model_type", type="string"),
        Column(name="feature_set_versions", type="string"),
        Column(name="train_start_ns", type="int64"),
        Column(name="train_end_ns", type="int64"),
        Column(name="validation_start_ns", type="int64"),
        Column(name="validation_end_ns", type="int64"),
        Column(name="code_commit", type="string"),
        Column(name="hyperparameters", type="string"),
        Column(name="scaler_parameters", type="string"),
        Column(name="calibration_model", type="string"),
        Column(name="metrics", type="string"),
        Column(name="deployment_status", type="string"),
        Column(name="validation_regime", type="string"),
        # PRD §0 item 13's "versioned dataset" ([[REQ-WP-040]]): which table,
        # which snapshot, and what was under it. The hash is the claim; the id
        # is only a name.
        Column(name="dataset_table", type="string"),
        Column(name="dataset_snapshot_id", type="int64"),
        Column(name="dataset_content_hash", type="string"),
    ),
    event_time_column="event_time_ns",
)


@dataclass(frozen=True)
class ModelRegistry:
    """PRD §23.9's registrations, on the canonical plane."""

    catalog: Catalog

    @property
    def table(self) -> IcebergTable:
        return IcebergTable(
            name=MODEL_REGISTRY_TABLE, schema=MODEL_REGISTRY_SCHEMA, catalog=self.catalog
        )

    def record(self, entries: Sequence[Registration]) -> None:
        """Store registrations the registry does not already hold.

        Skipping what it holds rather than appending, for [[ADR-056]]'s reason:
        the plane rejects nothing, so a re-registration would leave one artifact
        described twice and `entries()` would report two models where there is
        one. The artifact hash is the identity, so two entries sharing it are
        the same artifact by construction.
        """
        if not entries:
            raise ValueError("recording nothing would commit a snapshot that says nothing")
        known = self.artifacts()
        fresh = [entry for entry in entries if entry.artifact_hash not in known]
        if fresh:
            self.table.append([_as_row(entry) for entry in fresh])

    def entries(self) -> tuple[Registration, ...]:
        """Every registration on record, oldest first."""
        return tuple(_from_row(row) for row in self.table.read().to_pylist())

    def artifacts(self) -> frozenset[str]:
        """Every artifact hash on record."""
        return frozenset(entry.artifact_hash for entry in self.entries())

    def holds(self, artifact: str) -> bool:
        return artifact in self.artifacts()


def require_registered(identity: RunIdentity, *, models: ModelRegistry) -> None:
    """Refuse a run citing an artifact nobody registered.

    A hash nobody can resolve is a different kind of unreproducible from no hash
    at all: the run looks checked, and the string is the only evidence. A run
    that fitted nothing (`NO_MODEL`) needs no registration -- requiring one would
    refuse every ablation and replay in the repository.
    """
    artifact = identity.model_artifact
    if isinstance(artifact, ModelAbsence):
        return
    if not models.holds(artifact):
        raise NotReproducible(
            f"model artifact {artifact[:8]}... is cited by this run and is in no "
            "registration; a hash nobody can resolve certifies nothing, and PRD "
            "section 0 item 13 asks for an artifact rather than a string"
        )


def combined_artifact(parts: Sequence[str]) -> str:
    """One artifact hash over a variant's folds.

    A variant is fitted once per fold, and what a result cites is the variant
    *as run* -- the whole set. Registering each fold separately would produce
    artifacts nothing cites and leave the run's own identity ambiguous between
    them.

    Order matters and is the caller's: fold one and fold two are not
    interchangeable, and a hash that sorted them would call two different
    walk-forward orders the same run.
    """
    if not parts:
        raise ModelNotFitted(
            "a variant with no scored fold has no artifact; combining nothing would "
            "produce a stable hash that every empty variant would share"
        )
    digest = hashlib.sha256()
    for part in parts:
        _part(digest, _TAG_STR, part.encode())
    return digest.hexdigest()


def _as_row(entry: Registration) -> dict[str, object]:
    return {
        "event_time_ns": entry.train_start_ns,
        "artifact_hash": entry.artifact_hash,
        "model_type": entry.model_type,
        "feature_set_versions": json.dumps(dict(entry.feature_set_versions), sort_keys=True),
        "train_start_ns": entry.train_start_ns,
        "train_end_ns": entry.train_end_ns,
        "validation_start_ns": entry.validation_start_ns,
        "validation_end_ns": entry.validation_end_ns,
        "code_commit": entry.code_commit,
        "hyperparameters": json.dumps(dict(entry.hyperparameters), sort_keys=True),
        "scaler_parameters": json.dumps(dict(entry.scaler_parameters), sort_keys=True),
        "calibration_model": entry.calibration_model,
        "metrics": json.dumps(dict(entry.metrics), sort_keys=True),
        "deployment_status": entry.deployment_status,
        "validation_regime": entry.validation_regime,
        "dataset_table": entry.dataset.table,
        "dataset_snapshot_id": entry.dataset.snapshot_id,
        "dataset_content_hash": entry.dataset.content_hash,
    }


def _from_row(row: dict[str, object]) -> Registration:
    """A registration back from its row.

    The artifact hash is read, never recomputed. A hash recomputed here would be
    a hash of this row -- it would survive every round trip and certify nothing
    about the model it claims to name.
    """
    return Registration(
        model_type=str(row["model_type"]),
        feature_set_versions=json.loads(str(row["feature_set_versions"])),
        train_start_ns=int(str(row["train_start_ns"])),
        train_end_ns=int(str(row["train_end_ns"])),
        validation_start_ns=int(str(row["validation_start_ns"])),
        validation_end_ns=int(str(row["validation_end_ns"])),
        code_commit=str(row["code_commit"]),
        hyperparameters=json.loads(str(row["hyperparameters"])),
        scaler_parameters=json.loads(str(row["scaler_parameters"])),
        calibration_model=str(row["calibration_model"]),
        metrics=json.loads(str(row["metrics"])),
        artifact_hash=str(row["artifact_hash"]),
        deployment_status=str(row["deployment_status"]),
        validation_regime=cast(ValidationRegime, str(row["validation_regime"])),
        dataset=DatasetOrigin(
            table=str(row["dataset_table"]),
            snapshot_id=int(str(row["dataset_snapshot_id"])),
            content_hash=str(row["dataset_content_hash"]),
        ),
    )
