"""Funding dispersion compares rates over a common interval (REQ-WP-050).

The fixture is each venue's own funding *history*, not a stated interval, so the
settlement period is derived from the venue's timestamps by the tests. That is
the difference between an assertion and a claim -- and the claim would be wrong,
because one of the four venues settles hourly and the others every eight hours.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import pytest

from channelflow.crossvenue.funding import (
    BPS,
    FundingDispersion,
    IrregularSchedule,
    NoDispersion,
    VenueFunding,
    funding_dispersion,
    normalise,
    settlement_interval_ns,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "derivatives" / "funding_history.jsonl"

MINUTE_NS = 60 * 1_000_000_000
HOUR_NS = 60 * MINUTE_NS
EIGHT_HOURS_NS = 8 * HOUR_NS
YEAR_NS = 365 * 24 * HOUR_NS


def _rows() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.funding_history_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


ROWS = _rows()
HISTORIES = [row for row in ROWS if row["kind"] == "funding_history"]
VENUES = [row["venue"] for row in HISTORIES]


def _interval(row: dict[str, Any]) -> int:
    return settlement_interval_ns([entry["time_ms"] for entry in row["settlements"]])


def _latest(row: dict[str, Any]) -> dict[str, Any]:
    return max(row["settlements"], key=lambda entry: entry["time_ms"])


def _readings() -> list[VenueFunding]:
    out = []
    for row in HISTORIES:
        latest = _latest(row)
        out.append(
            VenueFunding(
                venue_id=row["venue"],
                rate=float(latest["rate"]),
                interval_ns=_interval(row),
                observed_at_ns=latest["time_ms"] * 1_000_000,
            )
        )
    return out


def _at_ns() -> int:
    return max(reading.observed_at_ns for reading in _readings())


# --- the intervals are not the same --------------------------------------------


@pytest.mark.trace("REQ-WP-050")
@pytest.mark.parametrize("row", HISTORIES, ids=VENUES)
def test_each_venue_s_interval_comes_from_its_own_settlements(row: dict[str, Any]) -> None:
    interval = _interval(row)
    assert interval > 0
    # Within a second of a whole number of minutes: the venues settle on a
    # schedule, with jitter measured in milliseconds.
    assert (
        abs(interval % MINUTE_NS) < 1_000_000_000
        or abs(MINUTE_NS - interval % MINUTE_NS) < 1_000_000_000
    )


@pytest.mark.trace("REQ-WP-050")
def test_one_venue_settles_eight_times_as_often_as_the_others() -> None:
    """The finding this requirement exists for.

    Without normalising, that factor of eight is in the dispersion before the
    market has said anything.
    """
    intervals = {row["venue"]: _interval(row) for row in HISTORIES}
    shortest = min(intervals.values())
    longest = max(intervals.values())
    assert longest / shortest == pytest.approx(8, rel=0.01), intervals
    assert len({round(value / MINUTE_NS) for value in intervals.values()}) == 2


@pytest.mark.trace("REQ-WP-050")
def test_a_schedule_too_irregular_for_one_interval_is_refused() -> None:
    """A venue that settles unevenly has no "rate per eight hours" to compare,
    and returning the median anyway would hand back a number that looks like
    one."""
    base = 1_700_000_000_000
    regular = [base + step * 480 * 60_000 for step in range(5)]
    assert settlement_interval_ns(regular) == 480 * 60 * 1_000_000_000

    ragged = [base, base + 60_000 * 480, base + 60_000 * 600, base + 60_000 * 1080]
    with pytest.raises(IrregularSchedule, match="not one schedule"):
        settlement_interval_ns(ragged)


@pytest.mark.trace("REQ-WP-050")
def test_the_interval_is_the_middle_gap_and_not_the_first_one() -> None:
    """The first gap is one observation, and a venue's schedule carries jitter.

    A gap four per cent off passes the regularity check -- it is meant to, since
    Binance's own history is not exact -- so taking it as the interval would put
    four per cent into every rate normalised against that venue, quietly and
    in one direction.
    """
    base = 1_700_000_000_000
    minute = 60_000
    offsets = [0, 499, 979, 1459, 1939, 2419]  # a 499-minute first gap, then 480s
    stamps = [base + offset * minute for offset in offsets]

    first_gap_ns = (stamps[1] - stamps[0]) * 1_000_000
    derived = settlement_interval_ns(stamps)
    assert derived == 480 * 60 * 1_000_000_000
    assert derived != first_gap_ns
    assert abs(first_gap_ns - derived) / derived > 0.03


@pytest.mark.trace("REQ-WP-050")
def test_one_gap_is_not_a_schedule() -> None:
    with pytest.raises(IrregularSchedule, match="at most one gap"):
        settlement_interval_ns([1, 2])


@pytest.mark.trace("REQ-WP-050")
def test_settlements_that_do_not_advance_are_refused() -> None:
    with pytest.raises(IrregularSchedule, match="strictly increasing"):
        settlement_interval_ns([1_000, 1_000, 2_000, 3_000])


# --- normalisation --------------------------------------------------------------


@pytest.mark.trace("REQ-WP-050")
def test_an_hourly_rate_is_eight_times_itself_over_eight_hours() -> None:
    assert normalise(0.0001, from_interval_ns=HOUR_NS, to_interval_ns=EIGHT_HOURS_NS) == (
        pytest.approx(0.0001 * BPS * 8)
    )
    assert normalise(0.0001, from_interval_ns=EIGHT_HOURS_NS, to_interval_ns=EIGHT_HOURS_NS) == (
        pytest.approx(0.0001 * BPS)
    )


@pytest.mark.trace("REQ-WP-050")
def test_normalisation_is_linear_and_not_compounded() -> None:
    """Funding accrues per period and is paid, not reinvested, so eight hourly
    payments are eight times one -- compounding them would model a position that
    rolls its funding back in, which is a different instrument."""
    rate = 0.01
    linear = normalise(rate, from_interval_ns=HOUR_NS, to_interval_ns=EIGHT_HOURS_NS)
    compounded = ((1 + rate) ** 8 - 1) * BPS
    assert linear == pytest.approx(rate * BPS * 8)
    assert linear != pytest.approx(compounded, rel=1e-3)


@pytest.mark.trace("REQ-WP-050")
def test_a_negative_rate_stays_negative() -> None:
    """Funding is signed by nature: it is negative when shorts pay."""
    assert normalise(-0.0001, from_interval_ns=HOUR_NS, to_interval_ns=EIGHT_HOURS_NS) < 0


@pytest.mark.trace("REQ-WP-050")
@pytest.mark.parametrize(("source", "target"), [(0, HOUR_NS), (HOUR_NS, 0), (-1, HOUR_NS)])
def test_an_interval_of_nothing_describes_no_period(source: int, target: int) -> None:
    with pytest.raises(ValueError, match="no period"):
        normalise(0.0001, from_interval_ns=source, to_interval_ns=target)


@pytest.mark.trace("REQ-WP-050")
def test_a_venue_reading_without_a_real_interval_is_refused() -> None:
    """The rate means nothing without it, and the type is what stops a caller
    supplying the first and forgetting the second."""
    with pytest.raises(ValueError, match="interval"):
        VenueFunding(venue_id="v", rate=0.0001, interval_ns=0, observed_at_ns=1)


# --- the dispersion itself -------------------------------------------------------


@pytest.mark.trace("REQ-WP-050")
def test_the_dispersion_covers_every_venue_in_the_fixture() -> None:
    result = funding_dispersion(_readings(), at_ns=_at_ns(), to_interval_ns=EIGHT_HOURS_NS)
    assert isinstance(result, FundingDispersion)
    assert set(result.contributors) == set(VENUES)
    assert result.excluded == {}
    assert result.contributor_count == len(VENUES)


@pytest.mark.trace("REQ-WP-050")
def test_normalising_changes_the_answer_on_real_data() -> None:
    """The point of the module, measured rather than argued.

    The raw spread is not merely different -- it is *narrower*, because the
    hourly venue's rate is a small number that looks like agreement until it is
    put on the same footing as the rest.
    """
    readings = _readings()
    result = funding_dispersion(readings, at_ns=_at_ns(), to_interval_ns=EIGHT_HOURS_NS)

    raw = [reading.rate * BPS for reading in readings]
    raw_spread = max(raw) - min(raw)
    assert result.spread_bps != pytest.approx(raw_spread, rel=0.01)
    assert result.spread_bps > raw_spread


@pytest.mark.trace("REQ-WP-050")
def test_the_hourly_venue_is_the_one_the_raw_figure_misrepresents() -> None:
    """Named rather than inferred: the venue whose interval is shortest is the
    one whose raw rate understates it, by exactly the interval ratio."""
    readings = {reading.venue_id: reading for reading in _readings()}
    hourly = min(readings.values(), key=lambda reading: reading.interval_ns)
    result = funding_dispersion(
        list(readings.values()), at_ns=_at_ns(), to_interval_ns=EIGHT_HOURS_NS
    )
    ratio = EIGHT_HOURS_NS / hourly.interval_ns
    assert ratio == pytest.approx(8, rel=0.01)
    assert result.per_venue_bps[hourly.venue_id] == pytest.approx(hourly.rate * BPS * ratio)


@pytest.mark.trace("REQ-WP-050")
def test_the_three_figures_answer_three_questions() -> None:
    result = funding_dispersion(_readings(), at_ns=_at_ns(), to_interval_ns=EIGHT_HOURS_NS)
    values = list(result.per_venue_bps.values())
    assert result.median_bps == pytest.approx(statistics.median(values))
    assert result.spread_bps == pytest.approx(max(values) - min(values))
    assert result.stdev_bps == pytest.approx(statistics.pstdev(values))


@pytest.mark.trace("REQ-WP-050")
def test_the_spread_is_signed_aware() -> None:
    """A market where two venues pay longs and two pay shorts is wide, and a
    dispersion over absolute values would call it tight."""
    split = [
        VenueFunding(venue_id="a", rate=0.0001, interval_ns=EIGHT_HOURS_NS, observed_at_ns=0),
        VenueFunding(venue_id="b", rate=-0.0001, interval_ns=EIGHT_HOURS_NS, observed_at_ns=0),
    ]
    result = funding_dispersion(split, at_ns=0, to_interval_ns=EIGHT_HOURS_NS)
    assert result.spread_bps == pytest.approx(2.0)
    assert result.median_bps == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-050")
def test_the_reporting_interval_is_the_caller_s() -> None:
    """Annualising bakes in 365 against 360 and simple against compounded, which
    belongs to whoever reads the number."""
    readings = _readings()
    eight = funding_dispersion(readings, at_ns=_at_ns(), to_interval_ns=EIGHT_HOURS_NS)
    annual = funding_dispersion(readings, at_ns=_at_ns(), to_interval_ns=YEAR_NS)
    assert annual.interval_ns == YEAR_NS
    assert annual.spread_bps == pytest.approx(eight.spread_bps * YEAR_NS / EIGHT_HOURS_NS)


@pytest.mark.trace("REQ-WP-050")
def test_a_dispersion_needs_an_interval_to_express_itself_over() -> None:
    with pytest.raises(ValueError, match="interval to express"):
        funding_dispersion(_readings(), at_ns=_at_ns(), to_interval_ns=0)


# --- who was excluded, and why ---------------------------------------------------


@pytest.mark.trace("REQ-WP-050")
def test_a_stale_venue_is_excluded_with_a_reason_not_carried_forward() -> None:
    """The tolerance is the venue's own interval: a reading older than that means
    the venue has settled again since, so the rate in hand is not the rate in
    force. Carrying it forward would narrow the dispersion by pretending a venue
    agrees."""
    readings = _readings()
    at_ns = _at_ns()
    hourly = min(readings, key=lambda reading: reading.interval_ns)

    result = funding_dispersion(readings, at_ns=at_ns + 2 * HOUR_NS, to_interval_ns=EIGHT_HOURS_NS)
    assert hourly.venue_id in result.excluded
    assert "past this venue's own" in result.excluded[hourly.venue_id]
    assert hourly.venue_id not in result.contributors
    assert hourly.venue_id not in result.per_venue_bps


@pytest.mark.trace("REQ-WP-050")
def test_the_staleness_tolerance_scales_with_the_venue() -> None:
    """Nothing arbitrary to tune: an hourly venue goes stale in an hour and an
    eight-hourly one in eight."""
    hourly = VenueFunding(venue_id="fast", rate=0.0001, interval_ns=HOUR_NS, observed_at_ns=0)
    slow = VenueFunding(venue_id="slow", rate=0.0001, interval_ns=EIGHT_HOURS_NS, observed_at_ns=0)
    fresh = VenueFunding(
        venue_id="fresh", rate=0.0001, interval_ns=HOUR_NS, observed_at_ns=2 * HOUR_NS
    )
    result = funding_dispersion(
        [hourly, slow, fresh], at_ns=2 * HOUR_NS, to_interval_ns=EIGHT_HOURS_NS
    )
    assert "fast" in result.excluded
    assert set(result.contributors) == {"slow", "fresh"}


@pytest.mark.trace("REQ-WP-050")
def test_a_reading_from_the_future_is_excluded() -> None:
    ahead = VenueFunding(venue_id="a", rate=0.0001, interval_ns=HOUR_NS, observed_at_ns=10)
    here = VenueFunding(venue_id="b", rate=0.0002, interval_ns=HOUR_NS, observed_at_ns=1)
    also = VenueFunding(venue_id="c", rate=0.0003, interval_ns=HOUR_NS, observed_at_ns=1)
    result = funding_dispersion([ahead, here, also], at_ns=5, to_interval_ns=HOUR_NS)
    assert result.excluded["a"] == "reading is later than the instant asked about"
    assert set(result.contributors) == {"b", "c"}


@pytest.mark.trace("REQ-WP-050")
def test_one_venue_is_not_a_dispersion() -> None:
    """[[REQ-WP-016]]'s objection to a median over one mid, for the same reason."""
    lone = [VenueFunding(venue_id="a", rate=0.0001, interval_ns=HOUR_NS, observed_at_ns=0)]
    with pytest.raises(NoDispersion, match="wearing a better name"):
        funding_dispersion(lone, at_ns=0, to_interval_ns=HOUR_NS)


@pytest.mark.trace("REQ-WP-050")
def test_every_venue_stale_is_refused_rather_than_reported_as_agreement() -> None:
    readings = _readings()
    long_after = _at_ns() + 365 * 24 * HOUR_NS
    with pytest.raises(NoDispersion):
        funding_dispersion(readings, at_ns=long_after, to_interval_ns=EIGHT_HOURS_NS)


# --- provenance -------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-050")
def test_the_fixture_carries_history_and_not_a_stated_interval() -> None:
    """A stated interval would be a claim; a history is evidence, and the claim
    would have been wrong for one venue in four."""
    assert len(HISTORIES) >= 4
    for row in HISTORIES:
        assert len(row["settlements"]) >= 3
        assert all({"time_ms", "rate"} <= set(entry) for entry in row["settlements"])
    assert "interval" not in {key for row in HISTORIES for key in row}
