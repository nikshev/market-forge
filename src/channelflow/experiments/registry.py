"""The experiment registry, on the canonical plane.

# @trace: REQ-REPRO-001
# @trace: REQ-BIAS-011

PRD §41 rule 11: "Store all discarded experiment variants to reduce silent
cherry-picking." PRD §29.B lists `backtest_runs` and `experiment_membership`
among the canonical tables. [[ADR-024]] recorded that rule 11 had no home
because nothing here did experiment tracking; this is that home.

The registry is a lakehouse table, which means it inherits three properties
without asking for them: its history is immutable, its commits are atomic, and
every version of it has a content hash of its own. A registry that could be
edited after the fact would defeat the rule it exists to enforce -- the whole
point of storing discarded variants is that the record cannot be tidied up
afterwards.

**Recording is unconditional.** A run that cannot be reproduced is still
recorded, and recorded as unreproducible. Refusing to record it would leave no
trace of it at all, which is the outcome rule 11 is against.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from channelflow.experiments.identity import ModelAbsence, ModelArtifact, RunIdentity
from channelflow.lakehouse import Column, ObjectStore, Schema, Table

#: PRD §29.B's `experiment_membership`, under a name that says what a row is.
TABLE_NAME = "experiment_runs"


class Outcome(StrEnum):
    """What became of a variant."""

    KEPT = "kept"
    DISCARDED = "discarded"


#: The registry's columns. `event_time_ns` is the experiment's own as-of instant
#: -- the point in the data the run was about -- and not a clock reading, so the
#: table can answer a point-in-time read like every other one on the plane.
SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="run_hash", type="string"),
        Column(name="experiment", type="string"),
        Column(name="variant", type="string"),
        Column(name="outcome", type="string"),
        Column(name="dataset", type="string"),
        Column(name="config", type="string"),
        Column(name="code_commit", type="string"),
        Column(name="code_dirty", type="bool"),
        Column(name="model_artifact", type="string"),
        Column(name="reproducible", type="bool"),
        Column(name="note", type="string"),
    ),
    event_time_column="event_time_ns",
)


@dataclass(frozen=True)
class Run:
    """One variant of one experiment, and what became of it."""

    experiment: str
    variant: str
    identity: RunIdentity
    outcome: Outcome
    #: The as-of instant the run was about, in event time. Not a clock reading:
    #: nothing in this repository records wall-clock time, and a registry that
    #: did would make two replays of one study produce different rows.
    as_of_ns: int
    note: str = ""

    def __post_init__(self) -> None:
        if not self.experiment or not self.variant:
            raise ValueError(
                "a run names an experiment and a variant; an unnamed variant cannot "
                "be told apart from the others it was chosen against"
            )

    def as_row(self) -> dict[str, object]:
        return {
            "event_time_ns": self.as_of_ns,
            "run_hash": self.identity.run_hash,
            "experiment": self.experiment,
            "variant": self.variant,
            "outcome": str(self.outcome),
            "dataset": self.identity.dataset,
            "config": self.identity.config,
            "code_commit": self.identity.code.commit,
            "code_dirty": self.identity.code.dirty,
            "model_artifact": str(self.identity.model_artifact),
            "reproducible": self.identity.reproducible,
            # Why it is not reproducible, in the row rather than in a separate
            # place: a reader looking at a false `reproducible` needs the reason
            # in front of them, not a second lookup.
            "note": self.note or "; ".join(self.identity.missing),
        }


@dataclass(frozen=True)
class RecordedRun:
    """A row read back out of the registry."""

    run_hash: str
    experiment: str
    variant: str
    outcome: Outcome
    reproducible: bool
    model_artifact: ModelArtifact
    note: str


@dataclass(frozen=True)
class Registry:
    """Append-only experiment history over an object store."""

    store: ObjectStore

    @property
    def table(self) -> Table:
        return Table(name=TABLE_NAME, schema=SCHEMA, store=self.store)

    def record(self, runs: Sequence[Run]) -> str:
        """Append these runs and return the registry's new content hash.

        Unconditional: an unreproducible run is recorded as unreproducible.
        Refusing it would leave no trace of it, which is the outcome PRD §41
        rule 11 exists to prevent.
        """
        if not runs:
            raise ValueError("recording nothing would commit a snapshot that says nothing")
        return self.table.append([run.as_row() for run in runs]).content_hash

    def runs(self) -> tuple[RecordedRun, ...]:
        """Everything the registry holds, oldest first."""
        rows = self.table.read().to_pylist()
        return tuple(
            RecordedRun(
                run_hash=str(row["run_hash"]),
                experiment=str(row["experiment"]),
                variant=str(row["variant"]),
                outcome=Outcome(str(row["outcome"])),
                reproducible=bool(row["reproducible"]),
                model_artifact=_artifact(str(row["model_artifact"])),
                note=str(row["note"]),
            )
            for row in rows
        )

    def hashes(self) -> frozenset[str]:
        """Every run hash on record, which is what the reporting gate checks."""
        return frozenset(run.run_hash for run in self.runs())


def _artifact(value: str) -> ModelArtifact:
    """A stored artifact field back into its two-kinded type.

    The absences round-trip as themselves rather than as strings that happen to
    read like them, so a caller comparing against `ModelAbsence.NO_MODEL` gets
    the answer rather than a near miss.
    """
    for absence in ModelAbsence:
        if value == str(absence):
            return absence
    return value
