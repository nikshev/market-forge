"""PRD section 33's Prometheus-compatible exposition.

# @trace: REQ-WP-036

Section 33 lists eleven metrics. A handful have producers in this repository;
most describe connectors and pipelines that do not run yet, and the whole
requirement is what happens to those.

**A metric nobody writes is absent from the exposition, not exported as zero.**
A gauge sitting at zero because nothing increments it is indistinguishable, on a
dashboard, from a healthy zero. Every alert built on it stays green forever, and
the failure it was meant to catch becomes invisible *and* believed to be
watched -- a worse position than having no dashboard, because a missing
dashboard is noticed and a green one is trusted.

That is why `register` does not create a series and `observe` does. Nearly every
metrics library does the opposite: a registered counter starts at zero, which is
convenient in a long-running process where everything is eventually incremented
and dishonest in one where half the producers are not written yet.

No client library, for the same reason plus three more: the official one assumes
a module-level global registry, a process collector reading `/proc`, and a
clock. [[ADR-018]] forbids the clock, and a global registry leaks one test's
metrics into the next.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from channelflow.alerting.models import AuditRecord
from channelflow.health import FeedHealth, HealthState

#: Prometheus' own rule for a metric name.
_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_LABEL = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class InvalidMetricName(ValueError):
    """Refused at registration, where it can be fixed.

    At scrape time the symptom is a dashboard that quietly stops updating, in
    production, seen by nobody until somebody asks why a graph is flat.
    """


class CounterWentBackwards(ValueError):
    """A counter was asked to decrease.

    Clamping would be a lie told quietly -- the counter keeps serving a
    plausible number. A counter going backwards is always a bug at the call
    site.
    """


class UnknownMetric(KeyError):
    """Observed without being registered: the type and help would be guesses."""


class MetricKind(StrEnum):
    """Section 33's list is counts and current values.

    No histogram: it needs bucket boundaries nobody has chosen, and choosing
    them here would be a research default wearing a decision's clothes
    (section 13.11).
    """

    COUNTER = "counter"
    GAUGE = "gauge"


#: Section 33's metrics that nothing in this repository produces, and why.
#:
#: Named rather than exported as zero, and rather than dropped from the list.
#: Those are the two failures this module exists to prevent: the first makes a
#: dashboard lie, the second makes the gap invisible.
UNIMPLEMENTED: tuple[tuple[str, str], ...] = (
    ("events/sec by connector", "no connector runs; nothing counts an event"),
    ("reconnects", "a health reading carries it, but no session reports one yet"),
    ("book resets", "the book is reconstructed in tests only"),
    ("ingest latency", "there is no ingestion path to time"),
    ("feature compute latency", "features are computed on demand, not on a pipeline"),
    ("channel compute latency", "the same"),
    ("signal count", "the signal machine has no runner"),
    ("DB insert latency", "writes go through the lakehouse plane, which nothing times"),
    ("queue depth", "there is no queue; ADR-018 made delivery synchronous"),
)


@dataclass
class MetricRegistry:
    """What is known, and nothing else.

    Registration records a name, a kind and a help string. It creates no series
    and makes nothing appear in `render`. A series exists once something has
    observed it.
    """

    _kinds: dict[str, MetricKind] = field(default_factory=dict)
    _help: dict[str, str] = field(default_factory=dict)
    _series: dict[str, dict[tuple[tuple[str, str], ...], float]] = field(default_factory=dict)

    def register(self, name: str, kind: MetricKind, help: str) -> None:
        if not _NAME.match(name):
            raise InvalidMetricName(f"{name!r} is not a valid Prometheus metric name")
        self._kinds[name] = kind
        self._help[name] = help

    def observe(self, name: str, value: float, **labels: str) -> None:
        """Record a reading. This is what makes a metric exist."""
        if name not in self._kinds:
            raise UnknownMetric(name)
        for label in labels:
            if not _LABEL.match(label):
                raise InvalidMetricName(f"{label!r} is not a valid Prometheus label name")

        key = tuple(sorted(labels.items()))
        series = self._series.get(name, {})
        if self._kinds[name] is MetricKind.COUNTER and key in series and value < series[key]:
            raise CounterWentBackwards(f"{name} was {series[key]} and was asked to become {value}")
        series[key] = float(value)
        # Assigned only once a reading exists. An earlier version used
        # `setdefault`, which put an empty series in the registry before the
        # counter guard could refuse -- and `render` grew a "skip empty series"
        # branch to cope. The mutation sweep found that branch unreachable:
        # every path through `setdefault` went on to assign. Removing the window
        # is the fix; the branch was the symptom.
        self._series[name] = series

    def render(self) -> str:
        """The exposition, containing only what has been observed."""
        lines: list[str] = []
        for name, series in self._series.items():
            lines.append(f"# HELP {name} {self._help[name]}")
            lines.append(f"# TYPE {name} {self._kinds[name].value}")
            for key, value in series.items():
                lines.append(f"{name}{_labels(key)} {_number(value)}")
        return "\n".join(lines)


def _labels(key: tuple[tuple[str, str], ...]) -> str:
    if not key:
        return ""
    inner = ",".join(f'{name}="{_escape(value)}"' for name, value in key)
    return "{" + inner + "}"


def _escape(value: str) -> str:
    """Backslash, quote and newline, in that order.

    A reason string reaching a label unescaped breaks the sample line, and
    Prometheus then drops it or reads it as a different series -- a monitoring
    failure whose only symptom is a graph that stopped moving.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _number(value: float) -> str:
    """Whole numbers without a trailing `.0`, which reads as a rate."""
    return str(int(value)) if value == int(value) else repr(value)


def delivery_failures(audit: Iterable[AuditRecord]) -> int:
    """Section 33's "Telegram delivery failures", from the audit itself.

    Derived rather than counted alongside: a counter someone must remember to
    bump silently stops when a new code path forgets it, and the metric stays
    flat while the thing it measures gets worse -- a monitoring failure that
    looks exactly like good news.
    """
    return sum(1 for record in audit if record.status != "delivered")


def stale_feeds(healths: Iterable[FeedHealth]) -> int:
    """Section 33's "stale feed count", from [[REQ-WP-035]]'s assessments."""
    return sum(1 for health in healths if health.state is not HealthState.GOOD)


def unimplemented_reasons() -> Mapping[str, str]:
    """The section 33 metrics nothing here produces, keyed by their PRD name."""
    return dict(UNIMPLEMENTED)
