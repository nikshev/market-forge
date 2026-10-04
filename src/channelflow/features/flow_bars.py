"""CVD and the trade-imbalance features, derived from the bars' stored aggressor split.

# @trace: REQ-WP-088

PRD section 15.4 defines delta and cumulative volume delta over trades, in notional. Every bar
the bar builder writes already carries the split by aggressor side -- `aggressive_buy_base`,
`aggressive_sell_base`, `delta_base` -- together with `trade_count`, `first_trade_id` and
`last_trade_id`, and `resample.fold` sums them for every higher timeframe from complete windows.
So the flow features are a pure function of the stored bars: nothing reads a trade, and the same
bars give the same rows in any pass or replay (Principle VII).

**Base units, knowingly** ([[ADR-068]]). The bar stores the side split in the asset's units and
only the quote *total*, so these are `*_base` features and nothing here is named `cvd` or
`delta_notional`: those registry entries keep describing the PRD's notional quantity.

**A running sum is wrong forever after one missed trade**, so CVD is kept within a *run*: a
stretch of consecutive bars with no missing bar and no detectable missed trade. A break starts
the next run at zero and increments `cvd_run`, so a reader can see where a line must not be
joined. Breaks come from the bars themselves:

- a gap in `open_time_ns` (a bar is missing);
- for a venue whose trade ids are sequential per symbol (`sequential_ids`; measured on live
  bars, Binance only), a jump between one bar's last id and the next bar's first;
- for the same venues, a bar whose id span does not equal its `trade_count`: trades were missed
  inside it, its delta is wrong, and a wrong sum is worse than a missing point. It produces no
  row, and breaks the run on both sides.

A bar still forming (`is_final` false) produces nothing. A row at bar `t` depends only on bars
at or before `t` (Principle I). A bar in which nothing traded is data (delta zero) and is not a
break; its normalised delta is absent rather than zero, because zero would say the buyers and
sellers balanced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from channelflow.bars.models import Bar
from channelflow.features.registry import FeatureSpec, register

SECOND_NS = 1_000_000_000

FLOW_FEATURES: tuple[str, ...] = (
    "delta_base",
    "cvd_base",
    "normalized_delta_base",
    "cvd_base_slope",
    "cvd_base_acceleration",
    "cvd_run",
)
#: The name `features.exposed_feature_names` reads (ADR-015).
FEATURES = FLOW_FEATURES


@dataclass(frozen=True)
class FlowRow:
    """One bar's flow features, at the bar's close. A feature that is absent is not in `values`."""

    at_ns: int
    values: dict[str, float]


def _ids(bar: Bar) -> tuple[int, int] | None:
    try:
        return int(bar.first_trade_id), int(bar.last_trade_id)
    except ValueError:
        return None


def _incomplete(bar: Bar) -> bool:
    """Trades were missed inside this bar: its id span is not its trade count."""
    ids = _ids(bar)
    if ids is None or bar.trade_count == 0:
        return False
    return ids[1] - ids[0] + 1 != bar.trade_count


def _id_jump(previous: Bar, bar: Bar) -> bool:
    before, after = _ids(previous), _ids(bar)
    if before is None or after is None:
        return False
    return after[0] != before[1] + 1


def flow_rows(bars: Sequence[Bar], *, sequential_ids: bool) -> list[FlowRow]:
    """The flow rows of one series' bars, in time order, whatever order they come in."""
    by_open: dict[int, Bar] = {}
    for bar in bars:
        if bar.is_final:
            by_open[bar.open_time_ns] = bar

    rows: list[FlowRow] = []
    run = 0
    cvd = Decimal(0)
    previous: Bar | None = None
    last_emitted = False
    previous_slope: float | None = None
    pending_break = False

    for open_time in sorted(by_open):
        bar = by_open[open_time]
        broken = previous is not None and (
            bar.open_time_ns != previous.open_time_ns + bar.timeframe_ns
            or (sequential_ids and _id_jump(previous, bar))
        )
        previous = bar

        if sequential_ids and _incomplete(bar):
            pending_break = True
            continue

        if last_emitted and (broken or pending_break):
            run += 1
            cvd = Decimal(0)
            previous_slope = None
        pending_break = False
        last_emitted = True

        seconds = bar.timeframe_ns / SECOND_NS
        cvd += bar.delta_base
        slope = float(bar.delta_base) / seconds
        values: dict[str, float] = {
            "delta_base": float(bar.delta_base),
            "cvd_base": float(cvd),
            "cvd_base_slope": slope,
            "cvd_run": float(run),
        }
        if bar.volume_base > 0:
            values["normalized_delta_base"] = float(bar.delta_base / bar.volume_base)
        if previous_slope is not None:
            values["cvd_base_acceleration"] = (slope - previous_slope) / seconds
        previous_slope = slope
        rows.append(FlowRow(at_ns=bar.close_time_ns, values=values))

    return rows


def _register_all() -> None:
    common = {
        "version": 1,
        "family": "trade_flow",
        "source_events": ("bar",),
        "availability_lag_ms": 0,
        "clipping": "none",
        "point_in_time_safe": True,
    }
    note = (
        "In base units, derived from the bar's stored aggressor split (ADR-068); "
        "the PRD section 15.4 quantity is notional and is not produced."
    )
    fixture = "tests/unit/features/test_flow_bars.py"
    register(
        FeatureSpec(
            name="delta_base",
            description=f"Aggressive buy volume minus aggressive sell volume of the bar. {note}",
            formula="aggressive_buy_base - aggressive_sell_base, per final bar",
            unit="base asset",
            lookback="the bar",
            cadence="per final bar",
            null_policy="zero when nothing traded; the bar's trade count distinguishes it",
            normalization="none; see normalized_delta_base",
            test_fixture=f"{fixture}::test_delta_and_cvd_are_hand_computed_for_three_bars",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_base",
            description=f"Cumulative delta within a run of consecutive bars. {note}",
            formula="CVD_t = CVD_{t-1} + delta_base_t within a run; restarts at the first "
            "bar's delta when cvd_run increments (a missing bar, or a detectable missed trade)",
            unit="base asset",
            lookback="since the start of the run",
            cadence="per final bar",
            null_policy="absent for a bar that is incomplete (missed trades) or still forming",
            normalization="none; an unbounded running total",
            test_fixture=f"{fixture}::test_a_missing_bar_ends_the_run_and_nothing_is_summed_across_it",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="normalized_delta_base",
            description=f"The bar's delta as a fraction of the bar's volume. {note}",
            formula="delta_base / volume_base",
            unit="ratio",
            lookback="the bar",
            cadence="per final bar",
            null_policy="absent, not zero, when volume_base is zero",
            normalization="a ratio in [-1, 1]",
            test_fixture=f"{fixture}::test_normalized_delta_is_the_delta_over_the_bars_volume",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_base_slope",
            description=f"How fast cumulative delta moved across the bar. {note}",
            formula="delta_base / bar seconds",
            unit="base asset per second",
            lookback="the bar",
            cadence="per final bar",
            null_policy="never null for an emitted bar",
            normalization="none; per-second rate",
            test_fixture=f"{fixture}::test_slope_is_delta_over_seconds_and_acceleration_"
            "is_absent_in_a_runs_first_bar",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_base_acceleration",
            description=f"Change of the CVD slope from the previous bar of the run. {note}",
            formula="(slope_t - slope_{t-1}) / bar seconds within a run",
            unit="base asset per second squared",
            lookback="two bars of the run",
            cadence="per final bar",
            null_policy="absent in a run's first bar: there is no previous slope",
            normalization="none",
            test_fixture=f"{fixture}::test_slope_is_delta_over_seconds_and_acceleration_"
            "is_absent_in_a_runs_first_bar",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_run",
            description="Which run of consecutive bars the row belongs to; the chart breaks "
            "its line when it changes. Zero for the series' first run, plus one at each break.",
            formula="count of breaks so far: a gap in open_time, a trade-id jump, "
            "or an incomplete bar",
            unit="count",
            lookback="the series",
            cadence="per final bar",
            null_policy="never null for an emitted bar",
            normalization="none",
            test_fixture=f"{fixture}::test_a_missing_bar_ends_the_run_and_nothing_is_summed_across_it",
            **common,  # type: ignore[arg-type]
        )
    )


_register_all()
