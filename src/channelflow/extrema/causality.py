"""What may run on the production path (PRD section 13A.28, Test D).

# @trace: REQ-WP-019
# @trace: REQ-NRT-D
# @trace: REQ-BIAS-002

Test D: "Production feature path fails validation if a transform declares
symmetric/centered future dependence."

The wording is a design instruction, not a detection one -- see ADR-022. A
transform says what it is, and the production path refuses the ones that look
forward. Inferring centredness in general is not achievable: a centered moving
average, a symmetric Savitzky-Golay window, `argrelextrema`, and a loop reading
`series[i + 1]` are the same defect and look nothing alike.

Both kinds of transform are legitimate and both will exist here. PRD section
13A.4's symmetric `k`-neighbourhood labels are centered by definition, and
section 13A.6 says plainly that "centered/offline peak-finding may only create
labels and diagnostics, never live signals". So research paths call no guard;
only the production path does.

The declaration is a claim, and a false one is not caught here. Test A is the
backstop: a transform peeking forward while declaring itself causal will change
an already-finalized output when future bars arrive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: Library functions whose whole purpose is centered smoothing or offline peak
#: finding. Not a general detector -- a short list of the specific things
#: someone reaches for when a causal filter is not smoothing enough.
FORBIDDEN_IMPORTS = (
    "argrelextrema",
    "find_peaks",
    "savgol_filter",
    "filtfilt",
    "centered_rolling",
)

#: Modules allowed to name a forbidden helper, and why. PRD §41 rule 2 is about
#: live features, so the default is that every module under `src/channelflow/`
#: is scanned and this list is the whole of the exception.
#:
#: Keyed by module rather than by package, because the only real case is one
#: file: exempting `extrema` would exempt every module beside this one, and
#: `extrema` is where the rule most wants to look.
#:
#: The reason is not decoration. An exemption without one cannot be told apart
#: from an oversight, and it is what the next reader has to disagree with. No
#: research module is here: PRD §13A.6 would permit one, and none needs it --
#: `derivative_turning` writes its own centred labeller rather than importing a
#: helper. An entry added for a case that has not arrived is an entry nobody
#: checked.
EXEMPT: dict[str, str] = {
    "extrema/causality.py": (
        "names the forbidden helpers in order to forbid them; the list has to "
        "live somewhere and this is the module that owns the rule"
    ),
}


def forbidden_in(source: str) -> tuple[str, ...]:
    """Every forbidden helper named anywhere in `source`.

    A substring match, not an import parse, for [[ADR-022]]'s reason: this is a
    tripwire and not a detector. Parsing imports would ignore a docstring and
    would also miss `getattr(scipy.signal, "savgol_filter")`, which trades a real
    hole for a cosmetic one. A module that mentions one of these in prose should
    say so out loud and be exempted, or should not mention it.
    """
    return tuple(helper for helper in FORBIDDEN_IMPORTS if helper in source)


class CenteredTransformRejected(ValueError):
    """A transform declaring future dependence was offered to the live path."""


@runtime_checkable
class Transform(Protocol):
    """Anything the engine applies to a series.

    `centered` has no default. A transform whose author did not consider the
    question cannot be constructed -- the same reasoning ADR-015 applied to the
    feature registry's fields.
    """

    # Read-only properties rather than variables: `CausalTransform` below is a
    # frozen dataclass, and a protocol asking for settable attributes cannot be
    # satisfied by one -- which would make this protocol stricter than its own
    # reference implementation.
    @property
    def name(self) -> str: ...

    @property
    def centered(self) -> bool: ...

    def apply(self, values: list[float]) -> list[float]: ...


@dataclass(frozen=True)
class CausalTransform:
    """A transform that looks only backward."""

    name: str
    centered: bool = False

    def apply(self, values: list[float]) -> list[float]:
        return values


def require_causal(transform: Transform) -> Transform:
    """The production path's guard.

    Called where a transform enters live computation, so the refusal names the
    transform and the rule rather than surfacing later as a strange result.
    """
    if transform.centered:
        raise CenteredTransformRejected(
            f"transform {transform.name!r} declares centered/symmetric future "
            "dependence and cannot run on the production path. PRD section 13A.6: "
            "centered peak-finding may create labels and diagnostics, never live "
            "signals. Use it in a research path instead."
        )
    return transform
