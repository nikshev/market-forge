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
from enum import Enum
from typing import Protocol, cast, runtime_checkable

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

    The member is `compared` rather than `field` because almost every comparison
    in the research package does `from dataclasses import field`, and a property
    of that name in the same class body is a collision waiting for the second
    person to add a defaulted attribute.

    Runtime-checkable because the check that keeps this rule enforced tests
    types it has never heard of -- see `tests/unit/research/test_gate_adoption.py`.
    """

    @property
    def compared(self) -> Field: ...


def config_of(variant: object) -> dict[str, ConfigValue]:
    """The configuration of one variant object: everything it exposes about itself.

    The class name travels with the state because two objects can carry
    identical fields and mean different things.

    A dataclass gives its fields, which is every real variant in the research
    package. Anything else gives its instance attributes, because a variant
    reaching here is a caller's object satisfying a Protocol -- `ChannelModel`
    and the rest are protocols, and requiring a dataclass would narrow a working
    API to serve a bookkeeping rule.

    **The identity is only as good as what the object exposes.** An object
    holding its configuration in a closure, or on its class rather than its
    instance, reports a config of its type alone, and two such objects that
    differ are recorded as the same run. Class attributes are deliberately not
    scraped: `dir()` would pull in methods, inherited constants, and properties
    that compute, so the config would depend on the shape of a class hierarchy
    rather than on the variant. Predictably incomplete beats unpredictably full.
    """
    if isinstance(variant, type):
        raise UnhashableConfig(
            f"{variant.__name__} is the class, not a variant of it; its configuration "
            "is whatever it was constructed with, and a class has not been constructed"
        )
    if isinstance(variant, Enum):
        # An enum member keeps its identity in `_value_`, which the underscore
        # filter below would drop -- leaving every member of one enum with the
        # same config. Found by running it: EXP-009's three corridor methods are
        # an enum, and all three hashed alike.
        return {"variant": type(variant).__name__, "value": str(variant.value)}
    # The second half repeats the guard above. `is_dataclass` accepts a class as
    # readily as an instance, and only the instance form narrows for the type
    # checker; the runtime answer is already settled.
    if dataclasses.is_dataclass(variant) and not isinstance(variant, type):
        return {
            "variant": type(variant).__name__,
            **{name: _stable(value) for name, value in dataclasses.asdict(variant).items()},
        }
    state = getattr(variant, "__dict__", {})
    return {
        "variant": type(variant).__name__,
        **{name: _stable(value) for name, value in state.items() if not name.startswith("_")},
    }


def _stable(value: object) -> ConfigValue:
    """A value that means the same thing on the next run.

    A function is not configuration; it is behaviour, and its object identity
    changes every time a factory builds one. EXP-012's turning methods hold
    exactly that -- `local_polynomial` returns a `Method` carrying a fresh
    closure per call -- and keeping the object made two identical runs produce
    two different configs. An identity that changes between identical runs is
    not an identity, so the qualified name stands in for it: stable, and still
    distinguishing between two genuinely different functions.

    `hashing.py` had already written down the shape of this failure -- "repr of
    an object includes its memory address on some types, which would make a
    config hash different on every run for a reason nobody would find". This is
    that, arriving through a dataclass field instead of a repr.

    **The limit**: two closures from one factory share a qualified name. Where
    that is the only difference between two variants, they are recorded as one
    run. In EXP-012 it is not -- the `name` field separates them -- but nothing
    here guarantees the next module is so lucky.
    """
    if callable(value):
        module = getattr(value, "__module__", "?")
        return f"{module}.{getattr(value, '__qualname__', '?')}"
    if isinstance(value, dict):
        return {str(key): _stable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_stable(item) for item in value)
    if isinstance(value, list):
        return [_stable(item) for item in value]
    # Anything else goes through as it is, and `config_hash` refuses it if it
    # has no canonical encoding. Validating twice would put the same rule in two
    # places, and this is not the one that owns it.
    return cast(ConfigValue, value)


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


def _artifact_for(
    variant: str, model: ModelArtifact | Mapping[str, ModelArtifact]
) -> ModelArtifact:
    """This variant's artifact, from one value or a mapping of them."""
    if isinstance(model, Mapping):
        return model.get(variant, ModelAbsence.NO_MODEL)
    return model


def report_comparison(
    comparison: Compared,
    *,
    experiment: str,
    dataset: str,
    code: CodeVersion,
    registry: Registry,
    model: ModelArtifact | Mapping[str, ModelArtifact] = ModelAbsence.NO_MODEL,
    as_of_ns: int,
) -> Reported:
    """Record every variant a comparison tried, and report the one it chose.

    `dataset`, `code`, `model` and `as_of_ns` are the caller's. A research
    function is pure over its inputs -- no store, no git, no clock -- and giving
    it any of the four would break [[REQ-REPRO-001]]'s FR-013, which this
    inherits rather than restates.

    `model` is one artifact for the whole field, or one per variant. The mapping
    form arrived with [[REQ-WP-024]] and is a finding about this function rather
    than about its caller: a comparison that *fits* its variants gives each a
    different artifact, and a single value would have recorded four models under
    one hash. [[SPEC-057-experiment-gate-adoption]] said in as many words that if
    adoption needed the gate to change, that was a finding to record rather than
    absorb -- so it is recorded here. A variant absent from the mapping falls
    back to `NO_MODEL`, which is the honest answer for a variant nothing fitted.
    """
    field = comparison.compared

    # Every identity before any write: a config that cannot be hashed is a
    # refusal about the field, and a registry holding half a field would be
    # worse than one holding none of it.
    identities = {
        name: RunIdentity(
            dataset=dataset,
            config=config_hash(dict(config)),
            code=code,
            model_artifact=_artifact_for(name, model),
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
