"""The dashboard draws what exists and states what does not (REQ-WP-055).

PRD §33 lists eleven metrics and nine of them have no producer. A dashboard with
eleven panels draws nine of them empty, and an empty panel is indistinguishable
from a healthy quiet system -- a flat line at the bottom reads as "nothing is
going wrong", which is precisely what nobody knows.

These tests hold the definition to the code rather than to a reader's eye,
because a panel querying a metric nobody writes and a panel querying a metric
that was renamed look identical on screen, and both look like a quiet system.
"""

from __future__ import annotations

import json

import pytest

from channelflow.metrics import MetricKind, MetricRegistry, unimplemented_reasons
from channelflow.observability import (
    DASHBOARD,
    Absence,
    Dashboard,
    Panel,
    queried_metrics,
    stated_absences,
)
from channelflow.observability.dashboard import STALE_FEEDS, TELEGRAM_DELIVERY_FAILURES


def _registry() -> MetricRegistry:
    """A registry knowing exactly what this repository can emit."""
    registry = MetricRegistry()
    registry.register(
        TELEGRAM_DELIVERY_FAILURES, MetricKind.COUNTER, "Telegram deliveries that failed"
    )
    registry.register(STALE_FEEDS, MetricKind.GAUGE, "feeds that have stopped updating")
    return registry


@pytest.mark.trace("REQ-WP-055")
def test_every_panel_queries_a_metric_something_can_emit() -> None:
    """A panel querying a name nothing registers draws an empty panel, which on
    screen is a quiet system."""
    registry = _registry()
    for metric in queried_metrics():
        # `observe` is what refuses an unregistered name, so it is the check.
        registry.observe(metric, 0.0)
    assert queried_metrics()


@pytest.mark.trace("REQ-WP-055")
def test_a_panel_for_a_metric_nobody_registers_is_refused() -> None:
    """The direction that matters: the test above passes trivially if `observe`
    accepted anything."""
    registry = _registry()
    with pytest.raises(KeyError):
        registry.observe("channelflow_invented_metric", 1.0)


@pytest.mark.trace("REQ-WP-055")
def test_every_unproduced_metric_is_stated_rather_than_drawn() -> None:
    """§33's nine, each with the reason the code already carries."""
    reasons = unimplemented_reasons()
    assert len(reasons) == 9

    stated = {absence.metric: absence.reason for absence in DASHBOARD.absences}
    assert stated == dict(reasons)


@pytest.mark.trace("REQ-WP-055")
def test_no_unproduced_metric_appears_as_a_panel() -> None:
    """Drawing one would be the empty panel this whole definition avoids."""
    stated = {absence.metric for absence in DASHBOARD.absences}
    for panel in DASHBOARD.panels:
        assert panel.metric not in stated
        assert panel.title not in stated


@pytest.mark.trace("REQ-WP-055")
def test_the_absences_are_derived_and_not_transcribed() -> None:
    """A copy would go stale the day somebody implements one of them, and the
    dashboard would keep explaining why a metric that now exists does not."""
    assert stated_absences() == DASHBOARD.absences
    assert {absence.metric for absence in stated_absences()} == set(unimplemented_reasons())


@pytest.mark.trace("REQ-WP-055")
def test_implementing_a_metric_moves_it_off_the_absence_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The direction that keeps the definition honest over time.

    When a producer appears, `UNIMPLEMENTED` loses an entry and the derived
    absences shrink with it -- so a dashboard still explaining why that metric
    does not exist would fail the test above rather than quietly misinform.
    """
    from channelflow import metrics as metrics_module

    shortened = tuple(entry for entry in metrics_module.UNIMPLEMENTED if entry[0] != "queue depth")
    monkeypatch.setattr(metrics_module, "UNIMPLEMENTED", shortened)

    after = {absence.metric for absence in stated_absences()}
    assert "queue depth" not in after
    assert len(after) == 8
    # And the committed dashboard, built at import time, still carries it --
    # which is exactly the staleness the test above would catch.
    assert "queue depth" in {absence.metric for absence in DASHBOARD.absences}


@pytest.mark.trace("REQ-WP-055")
def test_the_two_lists_together_cover_section_33() -> None:
    """A metric can be neither silently dropped nor silently counted twice."""
    drawn = len(DASHBOARD.panels)
    stated = len(DASHBOARD.absences)
    assert drawn + stated == 11
    assert drawn == 2


@pytest.mark.trace("REQ-WP-055")
def test_absences_travel_in_the_document() -> None:
    """A renderer that received only the panels would draw a dashboard that
    looks complete."""
    document = json.loads(DASHBOARD.to_json())
    assert len(document["panels"]) == 2
    assert len(document["absences"]) == 9
    assert all(entry["reason"] for entry in document["absences"])


@pytest.mark.trace("REQ-WP-055")
def test_every_panel_says_what_to_take_from_it() -> None:
    """A panel whose meaning lives only in the reader's head is a panel two
    readers disagree about."""
    for panel in DASHBOARD.panels:
        assert len(panel.reading) > 20


@pytest.mark.trace("REQ-WP-055")
def test_a_dashboard_is_comparable_by_value() -> None:
    """Frozen dataclasses throughout, so a definition can be diffed rather than
    eyeballed."""
    # Rebuilt element by element, not handed the same tuple: comparing a
    # dashboard against itself passes whether or not its parts compare by value,
    # which is how this test first missed that they did not.
    rebuilt = tuple(
        Panel(title=panel.title, metric=panel.metric, reading=panel.reading)
        for panel in DASHBOARD.panels
    )
    assert rebuilt is not DASHBOARD.panels
    assert rebuilt == DASHBOARD.panels
    assert rebuilt[0] == DASHBOARD.panels[0]
    assert rebuilt[0] is not DASHBOARD.panels[0]

    same = Dashboard(title=DASHBOARD.title, panels=rebuilt, absences=DASHBOARD.absences)
    assert same == DASHBOARD
    changed = Dashboard(
        title=DASHBOARD.title,
        panels=(*DASHBOARD.panels, Panel(title="x", metric="y", reading="z" * 30)),
        absences=DASHBOARD.absences,
    )
    assert changed != DASHBOARD
    assert Absence(metric="a", reason="b") != Absence(metric="a", reason="c")
