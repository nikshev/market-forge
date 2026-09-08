"""PRD section 23.5A's Target E, from REQ-WP-019's confirmed extrema.

# @trace: REQ-WP-017
# @trace: REQ-BIAS-003

    P(local_max_within_H | point_in_time_state)
    P(local_min_within_H | point_in_time_state)
    P(no_turn_within_H   | point_in_time_state)

Section 23.5A says plainly that "labels may be future-aware because they are
targets, but feature generation and fold construction must remain strictly
point-in-time". PRD section 41 rule 3 gives the condition under which a
future-requiring pivot is legal at all: "unless the feature availability time
is shifted to confirmation time".

REQ-WP-019's `ConfirmedExtremum` already carries that shift. `known_at` is when
the system could first have said the extremum happened, and it is what goes
into a label's `available_ns` -- never `extremum_time_ns`, which is when the
price occurred and which nobody could act on until later.

Labelling from `extremum_time` instead would produce a dataset that trains
beautifully. The label would be available before the market could have known
it, and every metric computed on it would look like an edge.
"""

from __future__ import annotations

from channelflow.dataset.models import Label
from channelflow.extrema import ConfirmedExtremum


class LabelUnavailable(ValueError):
    """The horizon runs past the data, so nothing can be said about it."""


def label_at(
    at_ns: int,
    *,
    horizon_ns: int,
    extrema: list[ConfirmedExtremum],
    data_end_ns: int,
) -> Label:
    """What happened in `(at_ns, at_ns + horizon_ns]`.

    Raises when the horizon extends past the data. An unfinished horizon is not
    a "no turn": there may well have been a turn in the part we cannot see, and
    recording absence as evidence of absence would teach a model that the end
    of every dataset is calm.
    """
    horizon_end_ns = at_ns + horizon_ns
    if horizon_end_ns > data_end_ns:
        raise LabelUnavailable(
            f"horizon ends at {horizon_end_ns}, past the data's end {data_end_ns}: "
            "an unfinished horizon is not a no-turn"
        )

    inside = [e for e in extrema if at_ns < e.extremum_time_ns <= horizon_end_ns]
    if not inside:
        return Label(
            label_class="NO_TURN",
            horizon_end_ns=horizon_end_ns,
            # With no extremum, the fact "nothing turned in this window" is
            # knowable once the window has passed, and not before.
            available_ns=horizon_end_ns,
        )

    first = min(inside, key=lambda e: e.extremum_time_ns)
    return Label(
        label_class="MAX" if first.extremum_type == "HIGH" else "MIN",
        horizon_end_ns=horizon_end_ns,
        # PRD section 41 rule 3: the availability is the confirmation time.
        available_ns=first.known_at_ns,
        extremum_time_ns=first.extremum_time_ns,
    )


def labels_for(
    as_of_times: list[int],
    *,
    horizon_ns: int,
    extrema: list[ConfirmedExtremum],
    data_end_ns: int,
) -> dict[int, Label]:
    """Label every instant that can be labelled. The rest are simply absent."""
    labelled: dict[int, Label] = {}
    for at_ns in as_of_times:
        try:
            labelled[at_ns] = label_at(
                at_ns, horizon_ns=horizon_ns, extrema=extrema, data_end_ns=data_end_ns
            )
        except LabelUnavailable:
            continue
    return labelled
