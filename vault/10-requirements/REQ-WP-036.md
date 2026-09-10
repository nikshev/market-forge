---
id: REQ-WP-036
title: A metric nobody writes is absent, not zero
type: work-package
prd_ref: "§33, §45 Phase 8"
prd_lines: "4783-4800, 6910"
phase: 8
status: implemented
depends_on: [REQ-WP-008, REQ-WP-035]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "monitoring dashboards;" and §33 says what they read:

    ## Metrics

    Prometheus-compatible:

    - events/sec by connector;
    - reconnects;
    - book resets;
    - ingest latency;
    - feature compute latency;
    - channel compute latency;
    - signal count;
    - Telegram delivery failures;
    - DB insert latency;
    - queue depth;
    - stale feed count.

**A metric nobody writes must be absent from the exposition, not exported as
zero.** This is the same rule this codebase has applied to features, ratios and
health readings, arriving in the place where it does the most damage. A gauge
sitting at zero because nothing increments it is indistinguishable, on a
dashboard, from a healthy zero. Every alert built on it stays green forever, and
the failure it was meant to catch is now invisible *and* believed to be watched
— which is worse than having no dashboard, because a missing dashboard is
noticed.

Eleven metrics are listed and a handful have producers today. Exporting all
eleven so the dashboard "looks complete" would be exactly the failure above,
performed deliberately.

**Prometheus-compatible means the text exposition format**, which is a contract
with something outside this repository: a name, optional labels, a value, and a
`# TYPE` line. Getting it subtly wrong produces a scrape that fails silently or,
worse, one that parses into the wrong series.

**No clock.** A metric is a reading at an instant that the caller supplies, as
every other reading in this system is — otherwise a replay produces different
metrics from the run it replays.

## Acceptance

- A metric with no recorded observation does not appear in the exposition.
- A metric observed with the value zero does appear, and reads as zero.
- The exposition parses as Prometheus text format: one `# TYPE` line per metric,
  names and labels well-formed, values numeric.
- Labels distinguish series that share a name — a per-connector metric with two
  connectors is two series, not a sum.
- Counters only increase; a counter asked to decrease is refused rather than
  silently clamped.
- Telegram delivery failures and stale feed count are derived from the audit and
  the health assessments that already exist, not from a parallel counter a caller
  must remember to bump.
- Metrics that no part of this system produces are named as unimplemented in one
  place, rather than exported as zero or silently omitted from the list.
- No wall clock anywhere; every instant is an argument.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-074-metrics]]
- **Tests:**
    - `tests/unit/metrics/test_registry.py::test_a_counter_refuses_to_go_backwards`
    - `tests/unit/metrics/test_registry.py::test_a_gauge_takes_the_latest_value`
    - `tests/unit/metrics/test_registry.py::test_a_label_value_is_escaped`
    - `tests/unit/metrics/test_registry.py::test_a_metric_never_appears_without_a_sample`
    - `tests/unit/metrics/test_registry.py::test_a_metric_observed_as_zero_is_present`
    - `tests/unit/metrics/test_registry.py::test_a_name_prometheus_would_reject_is_refused_at_registration`
    - `tests/unit/metrics/test_registry.py::test_a_refused_observation_leaves_the_exposition_untouched`
    - `tests/unit/metrics/test_registry.py::test_a_registered_metric_nobody_observed_is_absent`
    - `tests/unit/metrics/test_registry.py::test_an_empty_registry_renders_nothing_rather_than_a_page_of_zeroes`
    - `tests/unit/metrics/test_registry.py::test_delivery_failures_are_counted_from_the_audit`
    - `tests/unit/metrics/test_registry.py::test_every_rendered_metric_carries_its_type`
    - `tests/unit/metrics/test_registry.py::test_nothing_is_both_unimplemented_and_derived`
    - `tests/unit/metrics/test_registry.py::test_nothing_wrong_counts_as_nothing_wrong`
    - `tests/unit/metrics/test_registry.py::test_observing_one_metric_does_not_summon_the_others`
    - `tests/unit/metrics/test_registry.py::test_stale_feeds_are_counted_from_the_assessments`
    - `tests/unit/metrics/test_registry.py::test_the_help_line_travels_with_it`
    - `tests/unit/metrics/test_registry.py::test_the_metrics_nobody_produces_are_named`
    - `tests/unit/metrics/test_registry.py::test_two_connectors_are_two_series_not_a_sum`
- **Code:**
    - `src/channelflow/metrics.py`
- **Outcomes:** [[OUT-2026-09-10-implement-metrics]], [[OUT-2026-09-10-plan-metrics]], [[OUT-2026-09-10-requirement-metrics]], [[OUT-2026-09-10-spec-metrics]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

This is the exposition, not the dashboards. §45 lists "monitoring dashboards"
as one deliverable and this delivers the half that belongs in this repository; a
Grafana definition describes a deployment that does not exist yet, and the
remaining half stays in `not_delivered` where it can be disagreed with.

The rule at the top has a name in this vault already — [[ADR-016]] made it about
alert blocks, and [[REQ-WP-031]] about a ratio. It is the same rule.
