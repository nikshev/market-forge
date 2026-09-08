"""What may run on the production path (PRD section 13A.28, Test D).

# @trace: REQ-WP-019
# @trace: REQ-NRT-D

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


class CenteredTransformRejected(ValueError):
    """A transform declaring future dependence was offered to the live path."""


@runtime_checkable
class Transform(Protocol):
    """Anything the engine applies to a series.

    `centered` has no default. A transform whose author did not consider the
    question cannot be constructed -- the same reasoning ADR-015 applied to the
    feature registry's fields.
    """

    name: str
    centered: bool

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
