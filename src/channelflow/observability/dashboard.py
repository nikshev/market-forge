"""The monitoring dashboard, as a definition rather than a rendering.

# @trace: REQ-WP-055

PRD §45's Phase 8 asks for "monitoring dashboards" and §33 lists eleven metrics.
[[REQ-WP-036]] found that **nine of them have no producer**, and refused two
tempting ways out: exporting them as zero, which makes a dashboard lie, and
dropping them from the list, which makes the gap invisible.

A dashboard inherits that problem and makes it visual. Eleven panels would draw
nine of them empty, and **an empty panel is indistinguishable from a healthy
quiet system** -- a flat line at the bottom of a chart reads as "nothing is going
wrong", which is precisely what nobody knows.

So this definition has two kinds of entry. A `Panel` queries a metric something
can actually emit. An `Absence` states, in the words the code already carries,
why there is nothing to draw. The second kind is the reason this file exists;
without it the dashboard would be six honest panels and five missing ones, and
nobody looking at it would know which five.

**The definition is checked against the registry rather than by eye.** A panel
querying a metric nobody writes draws an empty panel; a metric renamed in the
code leaves a panel querying a name that no longer exists. On screen the two are
identical, and both are identical to a quiet system.

The drawing is the tool's problem -- Grafana, or anything that reads a JSON
definition. The same division `volumeProfile.ts` has lived with since
[[REQ-WP-012]]: the decision about what to show is tested here, the rendering is
not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from channelflow.metrics import unimplemented_reasons

#: Metrics this repository can emit, by the name they are registered under.
#: Both are [[REQ-WP-036]]'s: a count of Telegram delivery failures and a count
#: of feeds that have gone stale.
TELEGRAM_DELIVERY_FAILURES = "channelflow_telegram_delivery_failures_total"
STALE_FEEDS = "channelflow_stale_feeds"


@dataclass(frozen=True)
class Panel:
    """One thing the dashboard draws, and the metric it draws it from."""

    title: str
    metric: str
    #: What a reader should take from it. Not decoration: a panel whose meaning
    #: lives only in the reader's head is a panel two readers disagree about.
    reading: str


@dataclass(frozen=True)
class Absence:
    """One thing §33 asks for that nothing produces, and why.

    Carried with the same weight as a panel, because it answers the question a
    reader actually has -- "is this fine?" -- and an empty panel does not.
    """

    #: PRD §33's own wording, which is the key `unimplemented_reasons()` uses.
    metric: str
    reason: str


@dataclass(frozen=True)
class Dashboard:
    title: str
    panels: tuple[Panel, ...]
    absences: tuple[Absence, ...]

    def to_json(self) -> str:
        """A definition a renderer can read.

        Absences travel in the document rather than being dropped at the
        boundary: a renderer that received only the panels would draw a
        dashboard that looks complete.
        """
        return json.dumps(
            {
                "title": self.title,
                "panels": [
                    {"title": panel.title, "metric": panel.metric, "reading": panel.reading}
                    for panel in self.panels
                ],
                "absences": [
                    {"metric": absence.metric, "reason": absence.reason}
                    for absence in self.absences
                ],
            },
            indent=2,
            sort_keys=True,
        )


def stated_absences() -> tuple[Absence, ...]:
    """§33's metrics nothing produces, from the mapping the code already carries.

    Derived rather than transcribed. A copy would go stale the day somebody
    implements one of them, and the dashboard would keep explaining why a metric
    that now exists does not.
    """
    return tuple(
        Absence(metric=metric, reason=reason)
        for metric, reason in sorted(unimplemented_reasons().items())
    )


DASHBOARD = Dashboard(
    title="ChannelFlow — PRD §33",
    panels=(
        Panel(
            title="Telegram delivery failures",
            metric=TELEGRAM_DELIVERY_FAILURES,
            reading="a rising count means alerts are being written and not arriving",
        ),
        Panel(
            title="Stale feeds",
            metric=STALE_FEEDS,
            reading=(
                "how many feeds stopped updating. Zero here is a reading; an empty panel is not"
            ),
        ),
    ),
    absences=stated_absences(),
)


def queried_metrics(dashboard: Dashboard = DASHBOARD) -> frozenset[str]:
    """Every metric name the dashboard asks for."""
    return frozenset(panel.metric for panel in dashboard.panels)
