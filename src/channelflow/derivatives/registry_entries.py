"""Every derivatives feature, registered (PRD section 19).

# @trace: REQ-WP-013
# @trace: REQ-PRIN-008

ADR-015 made the registry a gate rather than a document, and REQ-WP-011's test
compares the exposed set against the registered one. That test is only about
the system if the enumeration reaches every package producing features -- so
this module registers, and `channelflow.features.exposed_feature_names` reads
`FEATURES` from here too.

A second package shipping unregistered features while the gate stayed green
would be the gate quietly becoming about one module.
"""

from __future__ import annotations

from channelflow.features.registry import FeatureSpec, register

FEATURES: tuple[str, ...] = (
    "funding_rate_settled",
    "funding_z",
    "funding_acceleration",
    "open_interest_usd",
    "oi_change_5m",
    "oi_change_1h",
    "oi_z",
    "oi_to_volume",
    "price_oi_regime",
    "basis_bps",
    "mark_premium_bps",
    "liquidation_long_usd_5m",
    "liquidation_short_usd_5m",
    "liquidation_imbalance_5m",
    "liquidation_intensity_5m",
    "time_since_liquidation_spike",
)

_DERIVATIVES = {
    "family": "derivatives",
    "source_events": ("derivatives_state",),
    "availability_lag_ms": 0,
    "clipping": "none",
    "point_in_time_safe": True,
}


def _register_all() -> None:
    register(
        FeatureSpec(
            name="funding_rate_settled",
            version=1,
            description="The most recently settled funding rate.",
            formula="the funding_rate of the latest state whose next_funding_time <= t",
            unit="rate per interval",
            lookback="instant",
            cadence="per funding interval",
            null_policy=(
                "absent when no interval has settled; an unsettled rate is never "
                "substituted (PRD section 41 rule 5)"
            ),
            normalization="none; see funding_z",
            test_fixture=(
                "tests/unit/derivatives/test_funding.py::test_an_unsettled_rate_is_not_used_at_t"
            ),
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="funding_z",
            version=1,
            description="How unusual the settled funding rate is against its own history.",
            formula="(rate - mean(window)) / stdev(window), over settled intervals only",
            unit="standard deviations",
            lookback="24 settled intervals, configurable",
            cadence="per funding interval",
            null_policy=(
                "absent on fewer observations than the window, and on a constant "
                "series; 0.0 would read as exactly average (ADR-026)"
            ),
            normalization="z-score against a trailing window",
            test_fixture="tests/unit/derivatives/test_funding.py::test_a_constant_series_has_no_z_score",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="funding_acceleration",
            version=1,
            description="The change in the change of settled funding.",
            formula="(r1 - r2) - (r2 - r3) over the three most recent settled intervals",
            unit="rate per interval squared",
            lookback="3 settled intervals",
            cadence="per funding interval",
            null_policy="absent on fewer than three settled intervals",
            normalization="none",
            test_fixture="tests/unit/derivatives/test_funding.py::test_acceleration_needs_three_intervals",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="open_interest_usd",
            version=1,
            description="Open interest in USD, as reported by the venue.",
            formula="the venue's own figure; never derived from base units and a price",
            unit="USD",
            lookback="instant",
            cadence="per state update",
            null_policy="absent when the venue reports base units only",
            normalization="none",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_base_only_states_are_skipped",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    for name, lookback in (("oi_change_5m", "5m"), ("oi_change_1h", "1h")):
        register(
            FeatureSpec(
                name=name,
                version=1,
                description=f"Change in open interest over {lookback}.",
                formula=(
                    "latest USD open interest minus the last observation at or before "
                    "the window's start"
                ),
                unit="USD",
                lookback=lookback,
                cadence="per state update",
                null_policy="absent when no observation precedes the window",
                normalization="none",
                test_fixture=(
                    "tests/unit/derivatives/test_openinterest.py"
                    "::test_change_is_measured_from_before_the_window"
                ),
                **_DERIVATIVES,  # type: ignore[arg-type]
            )
        )
    register(
        FeatureSpec(
            name="oi_z",
            version=1,
            description="How unusual open interest is against its own history.",
            formula="(oi - mean(window)) / stdev(window)",
            unit="standard deviations",
            lookback="20 observations, configurable",
            cadence="per state update",
            null_policy="absent on too few observations or a constant series (ADR-026)",
            normalization="z-score against a trailing window",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_oi_z_refuses_a_short_window",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="oi_to_volume",
            version=1,
            description="Open risk per unit of turnover.",
            formula="open_interest_usd / traded_volume_usd",
            unit="ratio",
            lookback="the volume window supplied by the caller",
            cadence="per state update",
            null_policy="absent on zero volume; never infinite and never zero",
            normalization="none; already a ratio",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_the_ratio_is_absent_on_no_volume",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="price_oi_regime",
            version=1,
            description=(
                "Which of PRD section 16.2's four quadrants price and open interest "
                "are jointly in. A label with no established directional meaning "
                "(ADR-027)."
            ),
            formula="sign(price change) crossed with sign(open interest change)",
            unit="categorical",
            lookback="the window supplied by the caller",
            cadence="per state update",
            null_policy="'undetermined' when either leg is flat",
            normalization="none; categorical",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_each_quadrant_is_labelled",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="basis_bps",
            version=1,
            description="Perpetual price against spot, relative to spot.",
            formula="(perp - spot) / spot * 10_000",
            unit="basis points",
            lookback="instant",
            cadence="per state update",
            null_policy="absent when either leg is missing",
            normalization="relative to spot, so comparable across price levels",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_basis_is_relative_to_spot",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="mark_premium_bps",
            version=1,
            description="Mark price against index, relative to the index.",
            formula="(mark - index) / index * 10_000",
            unit="basis points",
            lookback="instant",
            cadence="per state update",
            null_policy="absent when either leg is missing",
            normalization="relative to the index",
            test_fixture="tests/unit/derivatives/test_openinterest.py::test_the_mark_premium_is_relative_to_the_index",
            **_DERIVATIVES,  # type: ignore[arg-type]
        )
    )
    liquidation = {**_DERIVATIVES, "source_events": ("liquidation",)}
    for name, description in (
        ("liquidation_long_usd_5m", "Long notional liquidated in the last 5 minutes."),
        ("liquidation_short_usd_5m", "Short notional liquidated in the last 5 minutes."),
    ):
        register(
            FeatureSpec(
                name=name,
                version=1,
                description=description,
                formula="sum of notional_usd for that side within the window",
                unit="USD",
                lookback="5m",
                cadence="per liquidation",
                null_policy="zero when nothing was liquidated; the event count distinguishes it",
                normalization="none",
                test_fixture="tests/unit/derivatives/test_liquidations.py::test_sides_are_totalled_separately",
                **liquidation,  # type: ignore[arg-type]
            )
        )
    register(
        FeatureSpec(
            name="liquidation_imbalance_5m",
            version=1,
            description="Which side was liquidated more, normalized.",
            formula="(long_usd - short_usd) / (long_usd + short_usd)",
            unit="normalized",
            lookback="5m",
            cadence="per liquidation",
            null_policy=(
                "absent when nothing was liquidated; 0.0 means both sides equally, "
                "which is a fact about a busy window rather than a quiet one"
            ),
            normalization="none; already a ratio",
            test_fixture="tests/unit/derivatives/test_liquidations.py::test_the_imbalance_is_absent_when_nothing_was_liquidated",
            **liquidation,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="liquidation_intensity_5m",
            version=1,
            description="Liquidated notional as a fraction of turnover.",
            formula="liquidated_usd / traded_volume_usd",
            unit="ratio",
            lookback="5m",
            cadence="per liquidation",
            null_policy="absent on zero volume",
            normalization="none; already a ratio",
            test_fixture="tests/unit/derivatives/test_liquidations.py::test_intensity_is_absent_on_no_volume",
            **liquidation,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="time_since_liquidation_spike",
            version=1,
            description="Event-time distance to the last liquidation above a threshold.",
            formula="as_of - the event time of the most recent print >= the threshold",
            unit="nanoseconds",
            lookback="the whole stream",
            cadence="per liquidation",
            null_policy=(
                "absent when no spike has been seen -- different from a spike "
                "infinitely long ago, which any sentinel value would be plotted as"
            ),
            normalization="none",
            test_fixture="tests/unit/derivatives/test_liquidations.py::test_no_spike_is_absent_not_infinite",
            **liquidation,  # type: ignore[arg-type]
        )
    )


_register_all()
