"""PRD section 13A.11's forward path and its derivative roots (REQ-WP-019)."""

from __future__ import annotations

import pytest

from channelflow.turning import (
    PathCoefficients,
    TurnType,
    derivative_roots,
    slope_zeros,
)


@pytest.mark.trace("REQ-WP-019")
def test_the_path_and_its_derivatives_are_the_prds_own_formulas() -> None:
    """SC-004, FR-004.

    PRD section 13A.11 writes all three out. Checked against hand arithmetic at
    h = 2 for `1 + 2h + 3h^2 + 4h^3`: 1 + 4 + 12 + 32 = 49, the slope
    2 + 6h + 12h^2 = 2 + 12 + 48 = 62, and the curvature 6 + 24h = 54.
    """
    path = PathCoefficients(c0=1.0, c1=2.0, c2=3.0, c3=4.0, horizon=10.0)

    assert path.value(2.0) == pytest.approx(49.0)
    assert path.slope(2.0) == pytest.approx(62.0)
    assert path.curvature(2.0) == pytest.approx(54.0)


@pytest.mark.trace("REQ-WP-019")
def test_a_maximum_candidate_is_a_zero_slope_with_negative_curvature() -> None:
    """SC-004, FR-005, FR-006.

    `-(h - 3)^2` has its peak at h = 3, inside a horizon of 10.
    """
    # -(h-3)^2 = -h^2 + 6h - 9
    path = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0)

    roots = derivative_roots(path)

    assert len(roots) == 1
    assert roots[0].horizon == pytest.approx(3.0)
    assert roots[0].turn_type is TurnType.MAX
    assert path.slope(roots[0].horizon) == pytest.approx(0.0)
    assert roots[0].curvature < 0.0


@pytest.mark.trace("REQ-WP-019")
def test_a_minimum_candidate_is_the_mirror_image() -> None:
    """SC-004, FR-006."""
    path = PathCoefficients(c0=9.0, c1=-6.0, c2=1.0, c3=0.0, horizon=10.0)

    roots = derivative_roots(path)

    assert len(roots) == 1
    assert roots[0].turn_type is TurnType.MIN
    assert roots[0].curvature > 0.0


@pytest.mark.trace("REQ-WP-019")
def test_a_root_outside_the_horizon_is_not_a_candidate() -> None:
    """FR-005.

    The same peak at h = 3, with the horizon cut to 2. Section 13A.11's
    condition is `0 < h* <= H`, and a forecast about a horizon nobody asked
    about is an extrapolation wearing a prediction's clothes.
    """
    path = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=2.0)

    assert derivative_roots(path) == ()


@pytest.mark.trace("REQ-WP-019")
def test_a_root_at_zero_is_not_a_candidate() -> None:
    """FR-005.

    `h^2` turns at h = 0, which is now. Section 13A.11 writes `0 < h*`, strictly:
    a turn happening at this instant is not a forecast of one.
    """
    path = PathCoefficients(c0=0.0, c1=0.0, c2=1.0, c3=0.0, horizon=5.0)

    assert derivative_roots(path) == ()


@pytest.mark.trace("REQ-WP-019")
def test_a_straight_path_has_no_root() -> None:
    """FR-005.

    Its derivative is a non-zero constant. A path with no turn must produce no
    turn -- the case that would be easiest to paper over with a fallback.
    """
    path = PathCoefficients(c0=100.0, c1=2.0, c2=0.0, c3=0.0, horizon=10.0)

    assert derivative_roots(path) == ()


@pytest.mark.trace("REQ-WP-019")
def test_a_flat_path_produces_no_candidate_rather_than_every_horizon() -> None:
    """FR-005, FR-006.

    A constant path has a zero derivative everywhere. Every horizon is a root
    and none is a turn, so the honest answer is none.
    """
    path = PathCoefficients(c0=100.0, c1=0.0, c2=0.0, c3=0.0, horizon=10.0)

    assert derivative_roots(path) == ()


@pytest.mark.trace("REQ-WP-019")
def test_an_inflection_is_not_a_turn() -> None:
    """SC-005, FR-006.

    `h^3` has a zero derivative at h = 0 and a zero second derivative there too:
    the plateau PRD section 13A.11 names -- "price can plateau rather than
    reverse". Shifted to h = 2 so the root is inside the horizon and it is the
    curvature, not the position, that disqualifies it.
    """
    # (h-2)^3 = h^3 - 6h^2 + 12h - 8
    path = PathCoefficients(c0=-8.0, c1=12.0, c2=-6.0, c3=1.0, horizon=10.0)

    assert path.slope(2.0) == pytest.approx(0.0)
    assert path.curvature(2.0) == pytest.approx(0.0)
    assert derivative_roots(path) == ()


@pytest.mark.trace("REQ-WP-019")
def test_both_roots_of_a_cubic_are_returned() -> None:
    """SC-004, FR-007.

    Section 13A.11 lists "multiple derivative roots may exist" among the reasons
    a root is not sufficient evidence. Reporting one of two would hide exactly
    the ambiguity that limitation is about.

    `h^3 - 6h^2 + 9h` has slope `3h^2 - 12h + 9 = 3(h-1)(h-3)`: a maximum at
    h = 1 and a minimum at h = 3.
    """
    path = PathCoefficients(c0=0.0, c1=9.0, c2=-6.0, c3=1.0, horizon=10.0)

    roots = derivative_roots(path)

    assert [r.horizon for r in roots] == pytest.approx([1.0, 3.0])
    assert [r.turn_type for r in roots] == [TurnType.MAX, TurnType.MIN]


@pytest.mark.trace("REQ-WP-019")
def test_the_excursion_is_measured_from_now_not_from_the_intercept() -> None:
    """FR-005.

    Section 13A.12 condition 5 compares the predicted excursion against a fee
    and noise floor, and that comparison is only meaningful against the price
    now -- `P_hat(0)`.
    """
    path = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0)

    root = derivative_roots(path)[0]

    # P(0) = -9, P(3) = 0.
    assert root.excursion == pytest.approx(9.0)


@pytest.mark.trace("REQ-WP-019")
def test_a_horizon_that_is_not_positive_is_refused() -> None:
    """FR-004."""
    with pytest.raises(ValueError, match="horizon"):
        PathCoefficients(c0=0.0, c1=1.0, c2=0.0, c3=0.0, horizon=0.0)


@pytest.mark.trace("REQ-WP-019")
def test_every_solved_zero_really_zeroes_the_slope() -> None:
    """FR-005.

    `derivative_roots` discards anything at `h = 0` because section 13A.11 says
    `0 < h*`, which means a solver that invented a zero there would never be
    contradicted through it. This checks the solver itself, over one path of
    each degree: a straight path has no zero, a flat one has none to speak of,
    and every zero that is returned is a zero.
    """
    paths = (
        # cubic with two, quadratic with one, straight with none, flat.
        PathCoefficients(c0=0.0, c1=9.0, c2=-6.0, c3=1.0, horizon=10.0),
        PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0),
        PathCoefficients(c0=100.0, c1=2.0, c2=0.0, c3=0.0, horizon=10.0),
        PathCoefficients(c0=100.0, c1=0.0, c2=0.0, c3=0.0, horizon=10.0),
    )
    counts = [len(slope_zeros(path)) for path in paths]

    assert counts == [2, 1, 0, 0]
    for path in paths:
        for h in slope_zeros(path):
            assert path.slope(h) == pytest.approx(0.0, abs=1e-9)
