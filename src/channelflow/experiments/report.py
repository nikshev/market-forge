"""The gate between a run and a reportable result.

# @trace: REQ-REPRO-001
# @trace: REQ-BIAS-011

Two rules meet here, and neither is enforceable on its own.

PRD §0 item 13 says a result must be reproducible from four things. A record
that merely *stores* four fields satisfies nothing: the fields can be blank, the
commit can come from a dirty tree, and the result gets published anyway. What
makes the rule real is a gate the result has to pass, which refuses and says
which component is missing.

PRD §41 rule 11 says to store all discarded experiment variants, "to reduce
silent cherry-picking". Storing is not checkable -- nobody can know what was
considered and not written down. What *is* checkable is the shape of the claim:
reporting a winner means naming the field it won against, and every name in that
field has to already be in the registry. Cherry-picking then requires lying
about the field rather than merely staying quiet about it, which is a different
and much harder thing to do by accident.

That is the honest limit of the mechanism, and it is worth stating plainly: this
cannot stop someone who never mentions a variant. It stops the variant that was
run, lost, and quietly dropped -- which is the one rule 11 is actually about.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.experiments.identity import NotReproducible, RunIdentity
from channelflow.experiments.registry import Registry


class CherryPicked(ValueError):
    """A winner was reported without its whole field on record."""


@dataclass(frozen=True)
class Report:
    """A result that has passed both gates, and can say why it is trustworthy."""

    experiment: str
    winner: str
    winner_hash: str
    #: Every variant the winner was chosen from, its own hash included. A field
    #: of one is a legitimate report -- of a study that compared nothing.
    field: tuple[str, ...]
    dataset: str
    config: str
    code_commit: str

    @property
    def summary(self) -> str:
        return (
            f"{self.experiment}: {self.winner} chosen from {len(self.field)} variant(s), "
            f"reproducible from dataset {self.dataset[:12]}, config {self.config[:12]}, "
            f"commit {self.code_commit[:12]}"
        )


def publish(
    *,
    experiment: str,
    winner: str,
    identity: RunIdentity,
    considered: Sequence[tuple[str, RunIdentity]],
    registry: Registry,
) -> Report:
    """Report a winner, or refuse and say why.

    `considered` is the whole field, the winner included. Passing a field that
    omits the winner is refused: a result chosen from a set it was not in is not
    a choice anyone can check.
    """
    identity.require_reproducible()

    names = [name for name, _ in considered]
    if winner not in names:
        raise CherryPicked(
            f"{winner!r} is reported as the winner of {experiment} and is not among "
            f"the variants it was chosen from ({', '.join(names) or 'none'}); a "
            "result chosen from a set it was not in is not a choice anyone can check"
        )
    if len(set(names)) != len(names):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise CherryPicked(
            f"{', '.join(duplicates)} appears twice in {experiment}'s field; one "
            "variant counted twice makes the field look wider than it was"
        )

    on_record = registry.hashes()
    unrecorded = [name for name, variant in considered if variant.run_hash not in on_record]
    if unrecorded:
        raise CherryPicked(
            f"{', '.join(unrecorded)} were compared against {winner!r} and are not in "
            "the registry. PRD section 41 rule 11 asks for every discarded variant to "
            "be stored, and a field that is not on record is one nobody can check for "
            "the ones that lost"
        )

    return Report(
        experiment=experiment,
        winner=winner,
        winner_hash=identity.run_hash,
        field=tuple(names),
        dataset=identity.dataset,
        config=identity.config,
        code_commit=identity.code.commit,
    )


def why_not(identity: RunIdentity) -> str:
    """What stops this run being reportable, for a caller that would rather ask
    than catch.

    An empty string when nothing does -- the same answer `require_reproducible`
    gives by not raising, in a form that fits in a log line.
    """
    try:
        identity.require_reproducible()
    except NotReproducible as exc:
        return str(exc)
    return ""
