"""What a comparison compared, and the one way it reaches the registry.

# @trace: REQ-BIAS-011

[[REQ-REPRO-001]] built the registry and the gate. [[ADR-054]] then wrote down
what that had and had not achieved:

    Rule 11 is enforceable and not yet enforced. The mechanism exists; none of
    the seventeen research modules reports through it.

This is the other half, and its shape comes from ADR-054's own sentence: a
registry that is merely available is an honour system with a database attached.
So adoption is not eighteen modules gaining a call to `record`. It is the field
becoming something a comparison can be **asked** for -- because a comparison
that cannot answer is then a failing test, while a module that simply never
calls `record` looks exactly like one with nothing to report.

**A comparison that chose nothing is not made to choose.** Several experiments
deliberately report a whole field and no winner; `extremum_detectors` says so in
its own docstring. Forcing one would manufacture the very claim rule 11 exists
to make checkable. Recording is universal; the gate applies to a result that
chose.

**A variant's configuration is what distinguishes it, not its name.** Two of
EXP-001's five models are one class under two band options. Hashing the name
would give them one config and put two indistinguishable rows in the registry --
full coverage by row count, and worthless, because it reads as checked.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from channelflow.experiments.hashing import ConfigValue, UnhashableConfig, config_hash
from channelflow.experiments.identity import (
    CodeVersion,
    ModelAbsence,
    ModelArtifact,
    RunIdentity,
)
from channelflow.experiments.registry import Outcome, Registry, Run
from channelflow.experiments.report import Report, publish


@dataclass(frozen=True)
class Field:
    """The variants one comparison compared, and the one it chose, if any."""

    #: Variant name to the configuration that distinguishes it. A mapping rather
    #: than a sequence of pairs, so a field cannot name one variant twice -- the
    #: gate's duplicate refusal stays as the backstop for a caller assembling a
    #: field by hand, and becomes unreachable from a comparison.
    variants: Mapping[str, Mapping[str, ConfigValue]]
    #: `None` for a comparison that deliberately picked nothing, which is a
    #: different fact from one that picked and did not say.
    chosen: str | None = None

    def __post_init__(self) -> None:
        if not self.variants:
            raise ValueError(
                "a field with no variants is not a comparison; every variant in it "
                "would be on record vacuously, and the gate would pass it"
            )
        if self.chosen is not None and self.chosen not in self.variants:
            raise ValueError(
                f"{self.chosen!r} is not among the variants it was chosen from "
                f"({', '.join(sorted(self.variants))}); a result chosen from a set it "
                "was not in is not a choice anyone can check"
            )


@runtime_checkable
class Compared(Protocol):
    """A comparison that can say what it compared.

    Runtime-checkable because the check that keeps this rule enforced tests
    types it has never heard of -- see `tests/unit/research/test_gate_adoption.py`.
    """

    @property
    def field(self) -> Field: ...


def config_of(variant: object) -> dict[str, ConfigValue]:
    """The configuration of one variant object.

    The class name travels with the fields because two dataclasses can carry
    identical fields and mean different things.
    """
    if not dataclasses.is_dataclass(variant):
        raise UnhashableConfig(
            f"a {type(variant).__name__} carries no readable configuration; recording "
            "the variant under an empty one would say the run had no configuration, "
            "which is a different and false claim"
        )
    if isinstance(variant, type):
        raise UnhashableConfig(
            f"{variant.__name__} is the class, not a variant of it; its configuration "
            "is whatever it was constructed with, and a class has not been constructed"
        )
    return {"variant": type(variant).__name__, **dataclasses.asdict(variant)}


@dataclass(frozen=True)
class Reported:
    """What one report put on record."""

    recorded: int
    #: Variants already on record, which this call therefore did not write
    #: again. Counted rather than silent, for [[ADR-056]]'s reason: a re-run is
    #: a no-op and should look like one.
    skipped: int
    #: The gate's report, or nothing for a comparison that chose nothing.
    report: Report | None = None


def report_comparison(
    comparison: Compared,
    *,
    experiment: str,
    dataset: str,
    code: CodeVersion,
    registry: Registry,
    model: ModelArtifact = ModelAbsence.NO_MODEL,
    as_of_ns: int,
) -> Reported:
    """Record every variant a comparison tried, and report the one it chose.

    `dataset`, `code`, `model` and `as_of_ns` are the caller's. A research
    function is pure over its inputs -- no store, no git, no clock -- and giving
    it any of the four would break [[REQ-REPRO-001]]'s FR-013, which this
    inherits rather than restates.
    """
    field = comparison.field

    # Every identity before any write: a config that cannot be hashed is a
    # refusal about the field, and a registry holding half a field would be
    # worse than one holding none of it.
    identities = {
        name: RunIdentity(
            dataset=dataset,
            config=config_hash(dict(config)),
            code=code,
            model_artifact=model,
        )
        for name, config in field.variants.items()
    }

    # ADR-056 on a registry: the plane rejects nothing, so the writer has to.
    # Set membership rather than a timestamp -- an experiment's `as_of_ns` is
    # the caller's and two experiments can share one, while a run hash covers
    # all four components, so two runs sharing one are the same run.
    on_record = registry.hashes()
    fresh = [
        Run(
            experiment=experiment,
            variant=name,
            identity=identity,
            outcome=Outcome.KEPT if name == field.chosen else Outcome.DISCARDED,
            as_of_ns=as_of_ns,
        )
        for name, identity in identities.items()
        if identity.run_hash not in on_record
    ]
    if fresh:
        registry.record(fresh)

    report: Report | None = None
    if field.chosen is not None:
        # After recording, deliberately. The gate refuses a winner whose field
        # is not on record, and recording afterwards would make every first
        # report of an experiment fail.
        report = publish(
            experiment=experiment,
            winner=field.chosen,
            identity=identities[field.chosen],
            considered=[(name, identities[name]) for name in field.variants],
            registry=registry,
        )
    return Reported(recorded=len(fresh), skipped=len(field.variants) - len(fresh), report=report)
