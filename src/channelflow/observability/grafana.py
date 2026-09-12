"""The dashboard definition as a file Grafana can load.

# @trace: REQ-WP-056

[[REQ-WP-055]] defines what to show and why, and deliberately does not render
it. This renders it, into the one shape the tool in the stack reads.

**Generated rather than written.** A hand-written Grafana file would go stale the
day a metric gains a producer -- it would keep a panel for a metric that had
moved to the absence list, or keep explaining why a metric that now exists does
not. Both are a dashboard confidently wrong about its own coverage, which is the
failure [[REQ-WP-055]] derived its absences to avoid.

**The absences become text panels, not empty graphs.** That is the whole point
carried into the rendering: a graph of a metric nothing produces draws a flat
line at zero, and a flat line at the bottom of a chart reads as "nothing is going
wrong", which is precisely what nobody knows. A panel saying "no connector runs;
nothing counts an event" answers the question a reader actually has.
"""

from __future__ import annotations

import json

from channelflow.observability.dashboard import DASHBOARD, Dashboard

#: Grafana's schema version for the dashboard JSON this writes. Pinned rather
#: than omitted: Grafana migrates an unversioned dashboard on import and the
#: file on disk then stops matching what is displayed.
SCHEMA_VERSION = 39

#: Panels are laid out in a single column of full-width rows. A layout is not
#: data and nothing here tests it; it is written down so the file is loadable
#: rather than because the arrangement was chosen.
_PANEL_WIDTH = 24
_PANEL_HEIGHT = 8


def to_grafana(dashboard: Dashboard = DASHBOARD) -> dict[str, object]:
    """The definition as Grafana's dashboard document."""
    panels: list[dict[str, object]] = []
    row = 0

    for panel in dashboard.panels:
        panels.append(
            {
                "type": "timeseries",
                "title": panel.title,
                "description": panel.reading,
                "gridPos": {"h": _PANEL_HEIGHT, "w": _PANEL_WIDTH, "x": 0, "y": row},
                "id": len(panels) + 1,
                "targets": [{"expr": panel.metric, "refId": "A"}],
            }
        )
        row += _PANEL_HEIGHT

    for absence in dashboard.absences:
        panels.append(
            {
                # A text panel, not a graph. A graph of a metric nothing
                # produces draws a flat line at zero, and that reads as health.
                "type": "text",
                "title": f"{absence.metric} — not measured",
                "gridPos": {"h": 3, "w": _PANEL_WIDTH, "x": 0, "y": row},
                "id": len(panels) + 1,
                "options": {
                    "mode": "markdown",
                    "content": f"**Nothing produces this metric.** {absence.reason}",
                },
            }
        )
        row += 3

    return {
        "title": dashboard.title,
        "schemaVersion": SCHEMA_VERSION,
        "editable": False,
        "panels": panels,
    }


def render(dashboard: Dashboard = DASHBOARD) -> str:
    """The document as the file on disk, byte for byte.

    Sorted and indented so a regeneration produces a diff a reader can follow
    rather than a reordering.
    """
    return json.dumps(to_grafana(dashboard), indent=2, sort_keys=True) + "\n"
