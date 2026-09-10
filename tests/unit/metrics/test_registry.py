"""PRD §33's exposition, and what a metric nobody writes looks like (REQ-WP-036)."""

from __future__ import annotations

import pytest

from channelflow.alerting import AuditRecord
from channelflow.health import FeedHealth, HealthState
from channelflow.metrics import (
    UNIMPLEMENTED,
    CounterWentBackwards,
    InvalidMetricName,
    MetricKind,
    MetricRegistry,
    delivery_failures,
    stale_feeds,
)

BASE_NS = 1788838800000000000


def registry() -> MetricRegistry:
    r = MetricRegistry()
    r.register("channelflow_signals_total", MetricKind.COUNTER, "signals opened")
    r.register("channelflow_stale_feeds", MetricKind.GAUGE, "feeds not GOOD")
    return r


# --- absent, and zero ---------------------------------------------------------


@pytest.mark.trace("REQ-WP-036")
def test_a_registered_metric_nobody_observed_is_absent() -> None:
    """The whole requirement, in the behaviour that is the opposite of what
    nearly every metrics library does.

    A gauge sitting at zero because nothing increments it is indistinguishable,
    on a dashboard, from a healthy zero. Every alert built on it stays green
    forever, and the failure becomes invisible *and* believed to be watched.
    """
    assert registry().render() == ""


@pytest.mark.trace("REQ-WP-036")
def test_a_metric_observed_as_zero_is_present() -> None:
    """The other half, and it must be asserted beside the first.

    An implementation that dropped observed zeroes would satisfy the test above
    and would hide a genuinely quiet counter.
    """
    r = registry()
    r.observe("channelflow_stale_feeds", 0)

    assert "channelflow_stale_feeds 0" in r.render()


@pytest.mark.trace("REQ-WP-036")
def test_observing_one_metric_does_not_summon_the_others() -> None:
    r = registry()
    r.observe("channelflow_stale_feeds", 3)

    assert "channelflow_signals_total" not in r.render()


# --- what a scraper expects ---------------------------------------------------


@pytest.mark.trace("REQ-WP-036")
def test_every_rendered_metric_carries_its_type() -> None:
    r = registry()
    r.observe("channelflow_signals_total", 7)

    assert "# TYPE channelflow_signals_total counter" in r.render()


@pytest.mark.trace("REQ-WP-036")
def test_the_help_line_travels_with_it() -> None:
    r = registry()
    r.observe("channelflow_signals_total", 7)

    assert "# HELP channelflow_signals_total signals opened" in r.render()


@pytest.mark.trace("REQ-WP-036")
def test_two_connectors_are_two_series_not_a_sum() -> None:
    """A summed per-connector metric reports a healthy total while one connector
    is dead."""
    r = MetricRegistry()
    r.register("channelflow_events_total", MetricKind.COUNTER, "events seen")
    r.observe("channelflow_events_total", 10, connector="binance")
    r.observe("channelflow_events_total", 4, connector="bybit")

    text = r.render()
    assert 'channelflow_events_total{connector="binance"} 10' in text
    assert 'channelflow_events_total{connector="bybit"} 4' in text


@pytest.mark.trace("REQ-WP-036")
def test_a_label_value_is_escaped() -> None:
    """A reason string reaching a label unescaped breaks the line, and
    Prometheus then drops the sample or reads it as a different series."""
    r = MetricRegistry()
    r.register("channelflow_suppressed_total", MetricKind.COUNTER, "suppressed")
    r.observe("channelflow_suppressed_total", 1, reason='he said "stale"\nand left')

    line = r.render()
    assert r"\"stale\"" in line
    assert r"\n" in line
    # The sample sits on one line, whatever the label contained.
    assert len([ln for ln in line.splitlines() if ln.startswith("channelflow_suppressed")]) == 1


@pytest.mark.trace("REQ-WP-036")
def test_a_name_prometheus_would_reject_is_refused_at_registration() -> None:
    """Where it can be fixed, rather than at scrape time in production, where
    the symptom is a dashboard that quietly stops updating."""
    with pytest.raises(InvalidMetricName):
        MetricRegistry().register("channelflow-signals", MetricKind.COUNTER, "no hyphens")


@pytest.mark.trace("REQ-WP-036")
def test_a_gauge_takes_the_latest_value() -> None:
    r = registry()
    r.observe("channelflow_stale_feeds", 3)
    r.observe("channelflow_stale_feeds", 1)

    assert "channelflow_stale_feeds 1" in r.render()


@pytest.mark.trace("REQ-WP-036")
def test_a_counter_refuses_to_go_backwards() -> None:
    """A clamped decrement is a lie told quietly; the counter keeps serving a
    plausible number. A counter going backwards is always a bug."""
    r = registry()
    r.observe("channelflow_signals_total", 7)

    with pytest.raises(CounterWentBackwards):
        r.observe("channelflow_signals_total", 6)


@pytest.mark.trace("REQ-WP-036")
def test_an_empty_registry_renders_nothing_rather_than_a_page_of_zeroes() -> None:
    assert MetricRegistry().render() == ""


# --- derived from what already happened ---------------------------------------


@pytest.mark.trace("REQ-WP-036")
def test_delivery_failures_are_counted_from_the_audit() -> None:
    """A counter someone must remember to bump silently stops when a new code
    path forgets it, and the metric stays flat while the thing it measures gets
    worse."""
    import uuid

    def record(status: str) -> AuditRecord:
        return AuditRecord(
            signal_id=uuid.uuid4(),
            symbol="BTCUSDT",
            queued_at_ns=BASE_NS,
            status=status,  # type: ignore[arg-type]
            reason=status,
        )

    audit = [record("delivered"), record("dead_lettered"), record("suppressed")]

    assert delivery_failures(audit) == 2


@pytest.mark.trace("REQ-WP-036")
def test_stale_feeds_are_counted_from_the_assessments() -> None:
    def health(state: HealthState, feed: str) -> FeedHealth:
        return FeedHealth(feed=feed, state=state, reason="because", observed_at_ns=BASE_NS)

    healths = [
        health(HealthState.GOOD, "a"),
        health(HealthState.STALE, "b"),
        health(HealthState.INVALID, "c"),
    ]

    assert stale_feeds(healths) == 2


@pytest.mark.trace("REQ-WP-036")
def test_nothing_wrong_counts_as_nothing_wrong() -> None:
    """Zero here is a reading, and it will be exported as one."""
    assert delivery_failures([]) == 0
    assert stale_feeds([]) == 0


# --- what this system does not produce ----------------------------------------


@pytest.mark.trace("REQ-WP-036")
def test_the_metrics_nobody_produces_are_named() -> None:
    """Naming what does not exist is normally scope creep. Here it is the only
    alternative to the two failures this requirement is about: exporting an
    unproduced metric as zero, or dropping it from the list so nobody notices it
    is missing.
    """
    named = {name for name, _ in UNIMPLEMENTED}

    assert "events/sec by connector" in named
    assert "ingest latency" in named
    # Every entry says why, so the list cannot become a bare TODO.
    assert all(reason.strip() for _, reason in UNIMPLEMENTED)


@pytest.mark.trace("REQ-WP-036")
def test_nothing_is_both_unimplemented_and_derived() -> None:
    """The list would otherwise drift into naming things that grew producers."""
    named = {name for name, _ in UNIMPLEMENTED}

    assert "Telegram delivery failures" not in named
    assert "stale feed count" not in named


@pytest.mark.trace("REQ-WP-036")
def test_a_refused_observation_leaves_the_exposition_untouched() -> None:
    """A refusal is not a half-write.

    The registry once used `setdefault`, which put an empty series in place
    before the counter guard could refuse -- and `render` grew a branch to skip
    empty series. The mutation sweep found that branch unreachable, which is how
    the window came to light: the guard was the symptom, not the fix. This
    asserts the property both were reaching for.
    """
    r = registry()
    r.observe("channelflow_signals_total", 7)
    before = r.render()

    with pytest.raises(CounterWentBackwards):
        r.observe("channelflow_signals_total", 6)

    assert r.render() == before


@pytest.mark.trace("REQ-WP-036")
def test_a_metric_never_appears_without_a_sample() -> None:
    """No headers-only block. A `# TYPE` line with nothing beneath it is a
    metric announcing itself with no reading -- the absent-reads-as-present
    failure in its subtlest form, and a scraper records nothing for it while a
    dashboard shows the series exists."""
    r = registry()
    r.observe("channelflow_stale_feeds", 0)

    lines = r.render().splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# TYPE"):
            name = line.split()[2]
            assert any(later.startswith(name) for later in lines[index + 1 :]), name
