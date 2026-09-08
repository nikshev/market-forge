"""PRD section 13A.11's forward conditional path, and where its slope is zero.

# @trace: REQ-WP-019

    P_hat(h)     = c0 + c1*h + c2*h^2 + c3*h^3
    dP_hat/dh    = c1 + 2*c2*h + 3*c3*h^2
    d2P_hat/dh2  = 2*c2 + 6*c3*h

    "Forecast maximum candidate at h* if dP_hat/dh(h*) = 0 AND
     d2P_hat/dh2(h*) < 0 AND 0 < h* <= H."

The coefficients are label-side: they describe a forward path, which by PRD
section 24.2 a target may know and a feature may not. Nothing here reads a
feature, so nothing here can leak one.

This module holds no model and no data. Given four numbers it says where the
slope is zero, and that answer can be checked against a hand-solved quadratic --
which matters, because every refusal in `roots.py` is built on it being right.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

#: A curvature this close to zero is a floating-point zero, not a shallow turn.
#: The *market* question -- how much curvature is enough to act on -- is a
#: configured threshold in `roots.py`, deliberately not here.
CURVATURE_ZERO = 1e-12


class TurnType(StrEnum):
    MAX = "max"
    MIN = "min"


class PathCoefficients(BaseModel):
    """A cubic forward path over `h` in `[0, horizon]`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    c0: float
    c1: float
    c2: float
    c3: float
    #: `H` in section 13A.11's condition. Bounded by construction: an
    #: unbounded horizon makes "the root is inside the horizon" vacuous.
    horizon: float = Field(gt=0.0)

    def value(self, h: float) -> float:
        return self.c0 + self.c1 * h + self.c2 * h**2 + self.c3 * h**3

    def slope(self, h: float) -> float:
        return self.c1 + 2.0 * self.c2 * h + 3.0 * self.c3 * h**2

    def curvature(self, h: float) -> float:
        return 2.0 * self.c2 + 6.0 * self.c3 * h


@dataclass(frozen=True)
class RootCandidate:
    """One horizon where the forecast path turns, and by how much."""

    horizon: float
    turn_type: TurnType
    curvature: float
    #: Signed, and measured from `P_hat(0)` -- the price now. Section 13A.12's
    #: fifth condition compares it against a fee and noise floor, and that
    #: comparison is meaningless against anything else.
    excursion: float
    predicted_price: float


def derivative_roots(path: PathCoefficients) -> tuple[RootCandidate, ...]:
    """Section 13A.11's candidates, in horizon order.

    All of them: "multiple derivative roots may exist" is one of the reasons the
    section gives for a root not being sufficient evidence, and returning one of
    two would hide the ambiguity that limitation is about.
    """
    now = path.value(0.0)
    candidates = []
    for h in slope_zeros(path):
        if not 0.0 < h <= path.horizon:
            continue
        curvature = path.curvature(h)
        if abs(curvature) <= CURVATURE_ZERO:
            # An inflection, not a turn. Section 13A.11: "price can plateau
            # rather than reverse" -- and a plateau reported as a maximum is a
            # forecast of a reversal that was never forecast.
            continue
        candidates.append(
            RootCandidate(
                horizon=h,
                turn_type=TurnType.MAX if curvature < 0.0 else TurnType.MIN,
                curvature=curvature,
                excursion=path.value(h) - now,
                predicted_price=path.value(h),
            )
        )
    return tuple(sorted(candidates, key=lambda c: c.horizon))


def slope_zeros(path: PathCoefficients) -> tuple[float, ...]:
    """Solutions of `3*c3*h^2 + 2*c2*h + c1 = 0`, by degree.

    Public because it is the arithmetic every refusal downstream rests on, and
    because the horizon filter in `derivative_roots` would otherwise hide a
    wrong answer here: a spurious zero at `h = 0` is discarded by `0 < h*`
    whether or not the slope is actually zero there. Two guards over one
    property hide each other's absence.

    Each degree is its own case rather than one formula with a guard, because
    the degenerate ones are where a divide-by-zero would otherwise live.
    """
    a, b, c = 3.0 * path.c3, 2.0 * path.c2, path.c1

    if a == 0.0 and b == 0.0:
        # The slope is the constant `c1`. Either it is non-zero and there is no
        # root, or the path is flat and every horizon is one -- and a flat path
        # turns nowhere, so neither case yields a candidate.
        return ()
    if a == 0.0:
        return (-c / b,)

    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return ()
    root = math.sqrt(discriminant)
    return ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a))
