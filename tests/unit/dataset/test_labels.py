"""PRD section 23.5A's Target E (REQ-WP-017, REQ-BIAS-003).

Rule 3 of PRD section 41: "No pivot that requires future bars unless the
feature availability time is shifted to confirmation time."

REQ-WP-019's confirmed extrema carry that shift already. This is where it is
used, and the test below is the one that matters.
"""

from __future__ import annotations

import pytest

from channelflow.dataset import Label, LabelUnavailable, label_at, labels_for

from .conftest import BASE_NS, MINUTE_NS, extremum


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-003")
def test_a_labels_availability_is_the_confirmation_time_not_the_extremum() -> None:
    """SC-003, FR-006, PRD section 41 rule 3.

    The high happened at minute 20 and was confirmable at minute 25. A label
    available at minute 20 would let a model act on a fact five minutes before
    the market could have known it -- and every metric computed on that dataset
    would look like an edge.
    """
    label = label_at(
        BASE_NS + 10 * MINUTE_NS,
        horizon_ns=30 * MINUTE_NS,
        extrema=[extremum(at=20, known_at=25)],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert label.label_class == "MAX"
    assert label.available_ns == BASE_NS + 25 * MINUTE_NS
    assert label.extremum_time_ns == BASE_NS + 20 * MINUTE_NS
    assert label.available_ns > label.extremum_time_ns


@pytest.mark.trace("REQ-WP-017")
def test_a_low_becomes_a_min_label() -> None:
    """FR-007. A labeller handling one direction would pass the test above."""
    label = label_at(
        BASE_NS + 10 * MINUTE_NS,
        horizon_ns=30 * MINUTE_NS,
        extrema=[extremum(at=20, known_at=25, kind="LOW", price="90")],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert label.label_class == "MIN"


@pytest.mark.trace("REQ-WP-017")
def test_no_extremum_in_the_horizon_is_a_no_turn() -> None:
    """FR-007. And its availability is the horizon's end: "nothing turned" is
    knowable only once the window has passed."""
    label = label_at(
        BASE_NS + 10 * MINUTE_NS,
        horizon_ns=5 * MINUTE_NS,
        extrema=[extremum(at=50, known_at=55)],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert label.label_class == "NO_TURN"
    assert label.available_ns == BASE_NS + 15 * MINUTE_NS


@pytest.mark.trace("REQ-WP-017")
def test_an_extremum_outside_the_window_is_not_counted() -> None:
    """The window is `(t, t + H]`: half-open at the start, so an extremum at
    `t` itself belongs to the previous row's horizon, not this one's."""
    at_t = label_at(
        BASE_NS + 20 * MINUTE_NS,
        horizon_ns=10 * MINUTE_NS,
        extrema=[extremum(at=20, known_at=25)],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert at_t.label_class == "NO_TURN"


@pytest.mark.trace("REQ-WP-017")
def test_the_first_extremum_in_the_window_is_the_label() -> None:
    """Two turns in one horizon: the label is about the first, because that is
    what a model predicting "a turn within H" would be predicting."""
    label = label_at(
        BASE_NS + 10 * MINUTE_NS,
        horizon_ns=40 * MINUTE_NS,
        extrema=[
            extremum(at=40, known_at=45, kind="LOW", price="90"),
            extremum(at=20, known_at=25),
        ],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert label.label_class == "MAX"
    assert label.extremum_time_ns == BASE_NS + 20 * MINUTE_NS


@pytest.mark.trace("REQ-WP-017")
def test_an_unfinished_horizon_is_not_a_no_turn() -> None:
    """SC-004, FR-008, the spec's second edge case.

    There may well have been a turn in the part we cannot see. Recording
    absence as evidence of absence would teach a model that the end of every
    dataset is calm -- and the end of the dataset is where live trading starts.
    """
    with pytest.raises(LabelUnavailable, match="unfinished horizon"):
        label_at(
            BASE_NS + 95 * MINUTE_NS,
            horizon_ns=30 * MINUTE_NS,
            extrema=[],
            data_end_ns=BASE_NS + 100 * MINUTE_NS,
        )


@pytest.mark.trace("REQ-WP-017")
def test_rows_with_unfinished_horizons_are_simply_absent() -> None:
    """SC-004. `labels_for` returns what can be labelled; the join then drops
    the rest and counts them."""
    labelled = labels_for(
        [BASE_NS + i * MINUTE_NS for i in (10, 50, 95)],
        horizon_ns=30 * MINUTE_NS,
        extrema=[],
        data_end_ns=BASE_NS + 100 * MINUTE_NS,
    )

    assert sorted(labelled) == [BASE_NS + 10 * MINUTE_NS, BASE_NS + 50 * MINUTE_NS]


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-003")
def test_a_label_cannot_claim_to_predate_its_extremum() -> None:
    """FR-006, enforced by the type.

    The construction that would encode the leak is refused, so a labeller
    rewritten later cannot produce it by accident.
    """
    with pytest.raises(ValueError, match="13A.1"):
        Label(
            label_class="MAX",
            horizon_end_ns=BASE_NS + 40 * MINUTE_NS,
            available_ns=BASE_NS + 15 * MINUTE_NS,
            extremum_time_ns=BASE_NS + 20 * MINUTE_NS,
        )
