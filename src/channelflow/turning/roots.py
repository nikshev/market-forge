"""PRD section 13A.12's root filtering -- Test F (section 13A.28).

# @trace: REQ-WP-019
# @trace: REQ-NRT-F

    "Small perturbations within a configured tolerance must not create silently
     unstable promoted roots. Record root sensitivity metrics."

Section 13A.11 says why: "a root can appear from tiny coefficient changes."
A polynomial's derivative root is a ratio of estimated coefficients, and a ratio
near a boundary moves a long way for a small move in either term. Nothing about
the root itself announces this -- it is a number like any other, which is what
"silently" in Test F refers to.

So the root is recomputed over a deterministic lattice of perturbed paths, and
the three metrics section 13A.12 names are recorded on every assessment,
promoted or not. A rejected root's metrics are the ones a reader comes back to.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from channelflow.turning.path import PathCoefficients, RootCandidate, TurnType, derivative_roots

#: Each perturbed coefficient takes the tolerance down, unchanged, and up. Three
#: levels over three coefficients is 27 members: enough for a quartile to mean
#: something, small enough to stay exhaustive rather than sampled (ADR-041).
LEVELS: tuple[float, ...] = (-1.0, 0.0, 1.0)

#: Section 13A.12's conditions that need subsystems outside this module:
#: 2 (extrapolation bounds), 7 (data-quality state), 8 (walk-forward promotion
#: gate). Named in every decision rather than silently assumed, so a reader sees
#: a partial gate for what it is -- the same reason section 23.6's unrun
#: baselines are named in every comparison report.
DEFERRED_CONDITIONS: tuple[str, ...] = (
    "extrapolation_bounds",
    "data_quality_state",
    "walk_forward_promotion_gate",
)


@dataclass(frozen=True)
class RootStability:
    """Section 13A.12's example stability metrics, over the perturbed members."""

    #: Fraction of members that found a root inside the horizon at all.
    presence_rate: float
    #: Interquartile range of those members' root horizons. Section 13A.12 calls
    #: it `root_horizon_iqr_bars`; the unit is whatever `h` is measured in.
    horizon_iqr: float
    #: Fraction of the members that found a root and agreed on its direction.
    turn_type_agreement: float
    majority_turn_type: TurnType | None
    members: int
    tolerance: float
    member_horizons: tuple[float, ...] = field(default=())


@dataclass(frozen=True)
class PromotionDecision:
    """Whether a root may be promoted, and everything that decided it."""

    candidate: RootCandidate
    stability: RootStability
    promoted: bool
    #: The conditions that failed, by name. All of them -- a gate that stops at
    #: the first sends the reader back to run it again with that one fixed.
    failed: tuple[str, ...]
    #: The conditions this gate cannot evaluate. Never counted as passing.
    deferred: tuple[str, ...] = DEFERRED_CONDITIONS


@dataclass(frozen=True)
class PromotionGate:
    """Section 13A.12's conditions, with its own research defaults.

    The section states in its own words that these figures "are research
    defaults, not assumed production constants". That sentence is why they are
    fields with defaults rather than literals in the comparisons.
    """

    minimum_presence_rate: float = 0.70
    maximum_horizon_iqr: float = 3.0
    minimum_turn_type_agreement: float = 0.80
    #: Condition 6. Zero would admit the plateau `path.py` already excludes;
    #: a real deployment sets this from the instrument's own noise.
    minimum_curvature: float = 0.0
    #: Condition 5, in the path's own price units: fees plus the noise floor.
    noise_floor: float = 0.0

    def assess(self, candidate: RootCandidate, stability: RootStability) -> PromotionDecision:
        """Every condition, every failure named.

        Condition 1 (`0 < h* <= H_max`) is not re-checked here: `derivative_roots`
        will not construct a candidate that violates it, so a check would be
        testing that function rather than this one.
        """
        failed: list[str] = []
        if stability.presence_rate < self.minimum_presence_rate:
            failed.append("root_presence_rate")
        if stability.horizon_iqr > self.maximum_horizon_iqr:
            failed.append("root_horizon_iqr")
        if (
            stability.turn_type_agreement < self.minimum_turn_type_agreement
            or stability.majority_turn_type is not candidate.turn_type
        ):
            failed.append("turn_type_agreement")
        if abs(candidate.excursion) <= self.noise_floor:
            failed.append("noise_floor")
        if abs(candidate.curvature) < self.minimum_curvature:
            failed.append("minimum_curvature")

        return PromotionDecision(
            candidate=candidate,
            stability=stability,
            promoted=not failed,
            failed=tuple(failed),
        )


def assess_root_stability(path: PathCoefficients, *, tolerance: float) -> RootStability:
    """Recompute the path's first root over a lattice of perturbed paths.

    The lattice is deterministic and exhaustive rather than resampled
    ([[ADR-041]]): Constitution Principle XI asks for reproducible results, and
    a stability metric that moves between runs is the same instability one level
    up.

    A coefficient that is exactly zero is left alone. Zero there is a statement
    about the path's degree -- a quadratic is not a cubic with a small cubic
    term -- and scaling it up from nothing would perturb the shape rather than
    the estimate.
    """
    if tolerance <= 0.0:
        raise ValueError(
            "tolerance must be positive: a tolerance of zero perturbs nothing, so "
            "every member is the original path and the presence rate is 1 by "
            "construction -- a stability check that cannot fail"
        )

    reference = derivative_roots(path)
    horizons: list[float] = []
    types: list[TurnType] = []
    members = 0

    for da in LEVELS:
        for db in LEVELS:
            for dc in LEVELS:
                members += 1
                member = PathCoefficients(
                    c0=path.c0,
                    c1=path.c1 * (1.0 + da * tolerance),
                    c2=path.c2 * (1.0 + db * tolerance),
                    c3=path.c3 * (1.0 + dc * tolerance),
                    horizon=path.horizon,
                )
                found = _nearest(derivative_roots(member), reference)
                if found is None:
                    continue
                horizons.append(found.horizon)
                types.append(found.turn_type)

    if not horizons:
        return RootStability(
            presence_rate=0.0,
            horizon_iqr=0.0,
            turn_type_agreement=0.0,
            majority_turn_type=None,
            members=members,
            tolerance=tolerance,
        )

    majority = max(set(types), key=types.count)
    quartiles = np.percentile(np.array(horizons), [25.0, 75.0])
    return RootStability(
        presence_rate=len(horizons) / members,
        horizon_iqr=float(quartiles[1] - quartiles[0]),
        turn_type_agreement=types.count(majority) / len(types),
        majority_turn_type=majority,
        members=members,
        tolerance=tolerance,
        member_horizons=tuple(horizons),
    )


def _nearest(
    found: tuple[RootCandidate, ...], reference: tuple[RootCandidate, ...]
) -> RootCandidate | None:
    """The member's root closest to the unperturbed path's first one.

    With no reference root there is nothing for a member's root to be the
    perturbation of, so the whole assessment is about a root that does not
    exist -- reported as absent rather than as whatever the members happened to
    find.
    """
    if not found or not reference:
        return None
    target = reference[0].horizon
    return min(found, key=lambda c: abs(c.horizon - target))
