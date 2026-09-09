"""The channel that existed against the model's later state (REQ-US-003)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from channelflow.api import InMemoryRepository, create_app
from channelflow.api.channels import ChannelUnavailable
from channelflow.api.comparison import (
    HindsightInverted,
    compare_channel,
)

from .conftest import BASE_NS, MINUTE_NS, bar, snapshot

# The production fitter's lookback is 60 bars, so the history has to carry them
# before the instant being compared -- a shorter one would refuse the refit and
# the comparison would be untested rather than proven.
AT_NS = BASE_NS + 60 * MINUTE_NS
LATER_NS = BASE_NS + 69 * MINUTE_NS
BARS = 70


@pytest.fixture
def repo() -> InMemoryRepository:
    """A stored snapshot at minute sixty, and seventy minutes of bars."""
    repository = InMemoryRepository()
    for i in range(BARS):
        repository.add_bar(bar(i, 112000.0 + i * 10))
    repository.add_channel_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=AT_NS, center=112000.0),
    )
    return repository


@pytest.mark.trace("REQ-US-003")
def test_the_comparison_carries_both_channels_and_their_difference(
    repo: InMemoryRepository,
) -> None:
    """SC-001, FR-001, FR-002.

    PRD §27.5 calls the distinction critical because it "directly exposes
    repaint-like differences". Exposed through a toggle, the reader holds six
    numbers in their head and subtracts; the difference is the measurement.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    assert comparison.as_seen_then.as_of_ns == AT_NS
    assert comparison.current_refit.as_of_ns == LATER_NS
    assert comparison.difference.center == pytest.approx(
        comparison.current_refit.center_now - comparison.as_seen_then.center_now
    )
    assert comparison.difference.slope == pytest.approx(
        comparison.current_refit.slope_normalized - comparison.as_seen_then.slope_normalized
    )


@pytest.mark.trace("REQ-US-003")
def test_the_centre_movement_is_also_a_share_of_the_channels_width(
    repo: InMemoryRepository,
) -> None:
    """SC-002, FR-003.

    A hundred dollars of repaint means one thing on a channel five hundred wide
    and another on one worth five. Without the ratio, two instruments cannot be
    compared and neither can one instrument across regimes.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    then = comparison.as_seen_then
    width = then.upper_now - then.lower_now
    assert comparison.difference.center_in_widths == pytest.approx(
        comparison.difference.center / width
    )


@pytest.mark.trace("REQ-US-003")
def test_a_zero_width_channel_reports_no_ratio_rather_than_infinity(
    repo: InMemoryRepository,
) -> None:
    """SC-002, FR-004.

    Dividing by a zero width reports an infinite repaint, which reads as a
    catastrophic result rather than as a degenerate channel. The absolute deltas
    still stand.
    """
    repo.add_channel_snapshot(
        venue="binance",
        symbol="ETHUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=AT_NS, center=112000.0).model_copy(
            update={"upper_now": 112000.0, "lower_now": 112000.0}
        ),
    )
    for i in range(BARS):
        repo.add_bar(bar(i, 112000.0 + i * 10).model_copy(update={"symbol": "ETHUSDT"}))

    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="ETHUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    assert comparison.difference.center_in_widths is None
    assert comparison.difference.center is not None


@pytest.mark.trace("REQ-US-003")
def test_the_hindsight_span_is_stated(repo: InMemoryRepository) -> None:
    """SC-004, FR-007.

    The refit has seen four minutes the snapshot could not. That is the point of
    the comparison and the one thing that must never be mistaken for a
    point-in-time value, so it is a number in the answer rather than a fact
    about how it was called.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    assert comparison.hindsight_ns == LATER_NS - AT_NS


@pytest.mark.trace("REQ-US-003")
def test_no_hindsight_measures_model_drift_alone(repo: InMemoryRepository) -> None:
    """SC-004.

    With the later instant equal to the signal's, both channels see one
    information set, and any difference belongs to the model rather than to the
    data. A legitimate question, and a different one.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=AT_NS,
    )

    assert comparison.hindsight_ns == 0


@pytest.mark.trace("REQ-US-003")
def test_a_later_instant_that_is_earlier_is_refused(repo: InMemoryRepository) -> None:
    """SC-005, FR-008."""
    with pytest.raises(HindsightInverted):
        compare_channel(
            repo,
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=MINUTE_NS,
            at_ns=LATER_NS,
            now_ns=AT_NS,
        )


@pytest.mark.trace("REQ-US-003")
def test_a_missing_snapshot_refuses(repo: InMemoryRepository) -> None:
    """SC-003, FR-005.

    `AS-SEEN-THEN` cannot be reconstructed after the fact -- that is the
    guarantee it exists to make, and a comparison against a rebuilt one would
    measure nothing.
    """
    with pytest.raises(ChannelUnavailable):
        compare_channel(
            repo,
            venue="binance",
            symbol="SOLUSDT",
            timeframe_ns=MINUTE_NS,
            at_ns=AT_NS,
            now_ns=LATER_NS,
        )


@pytest.mark.trace("REQ-US-003")
def test_every_comparison_declares_itself_research_only(repo: InMemoryRepository) -> None:
    """SC-006, FR-009.

    A channel fitted over later bars will often look like it predicted what
    followed. Carried anywhere near a signal it is a look-ahead with a plausible
    face, so it says what it is in its own payload.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    assert comparison.research_only is True


@pytest.mark.trace("REQ-US-003")
def test_the_signal_path_does_not_import_the_comparison() -> None:
    """SC-007, FR-010, ADR-046.

    The same device [[ADR-040]] uses for lead-lag: intent cannot be checked, so
    the prohibition becomes a fact about the source tree.

    Import lines only, not the word. "Comparison" is ordinary English and
    appears in these packages' prose; a check that failed on a docstring would
    be renamed away rather than fixed, and would then be checking nothing.
    """
    root = Path(__file__).resolve().parents[3] / "src" / "channelflow"
    packages = ("signals", "alerting", "stops", "extrema")

    for package in packages:
        directory = root / package
        assert directory.is_dir(), f"{package} moved; this test would pass by finding nothing"
        for module in directory.glob("*.py"):
            imports = [
                line
                for line in module.read_text().splitlines()
                if line.startswith(("import ", "from "))
            ]
            assert not [line for line in imports if "comparison" in line], (
                f"{package}/{module.name} imports the repaint comparison, which is a "
                "channel fitted with hindsight"
            )


@pytest.mark.trace("REQ-US-003")
def test_a_version_difference_is_reported_not_refused(repo: InMemoryRepository) -> None:
    """FR-011.

    Comparing a stored snapshot against a newer model is a legitimate question,
    and refusing it would hide exactly the drift that only shows up that way.
    """
    comparison = compare_channel(
        repo,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=AT_NS,
        now_ns=LATER_NS,
    )

    assert comparison.as_seen_then.model_version
    assert comparison.current_refit.model_version


@pytest.mark.trace("REQ-US-003")
def test_the_comparison_is_reachable_over_http(repo: InMemoryRepository) -> None:
    """SC-001, FR-001.

    REQ-US-003 asks that the stored snapshot be "available for comparison". A
    function in the API package that no route reaches is available to this
    repository, not to the researcher.
    """
    client = TestClient(create_app(repository=repo))

    response = client.get(
        "/api/v1/channels/comparison",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": AT_NS,
            "now_ns": LATER_NS,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["research_only"] is True
    assert body["hindsight_ns"] == LATER_NS - AT_NS
    assert body["as_seen_then"]["mode"] == "AS-SEEN-THEN"
    assert body["current_refit"]["mode"] == "CURRENT REFIT"


@pytest.mark.trace("REQ-US-003")
def test_an_inverted_request_is_refused_over_http(repo: InMemoryRepository) -> None:
    """SC-005, FR-008.

    422 rather than 500: the request is well-formed and asks for something that
    is not a thing, which is the caller's to fix.
    """
    client = TestClient(create_app(repository=repo))

    response = client.get(
        "/api/v1/channels/comparison",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": LATER_NS,
            "now_ns": AT_NS,
        },
    )

    assert response.status_code == 422


@pytest.mark.trace("REQ-US-003")
def test_a_missing_snapshot_is_a_404(repo: InMemoryRepository) -> None:
    """SC-003, FR-005."""
    client = TestClient(create_app(repository=repo))

    response = client.get(
        "/api/v1/channels/comparison",
        params={
            "venue": "binance",
            "symbol": "SOLUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": AT_NS,
            "now_ns": LATER_NS,
        },
    )

    assert response.status_code == 404
