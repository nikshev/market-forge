"""The figure the product may quote: bar close to block time, per record (REQ-INFRA-007).

# @trace: REQ-INFRA-007

Per **record**, not per batch: a batch's block time minus each leaf's own bar close, so a record
that waited for a window to close shows the wait. The chain's time is the only clock on the
right-hand side; the local clock is never involved.

A sample that does not meet the success criterion (at least 50 records, 3 series and an hour) is
labelled insufficient. It is still reported -- an operator wants to see it -- but it is never
allowed to look like a result.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.submitter import outbox_states

SECOND_NS = 1_000_000_000
CRITERION_RECORDS = 50
CRITERION_SERIES = 3
CRITERION_WINDOW_S = 3600


@dataclass(frozen=True)
class LatencyReport:
    sample: int
    series: int
    window_s: int
    latencies_s: list[int]
    median_s: int
    p95_s: int
    max_s: int
    meets_criterion: bool
    verdict: str

    def as_json(self) -> dict[str, object]:
        out = asdict(self)
        out.pop("latencies_s")
        return out


def latency_report(catalog: Catalog, *, since_s: int) -> LatencyReport:
    confirmed = {
        str(b["batch_root"]): int(str(s["block_time_s"]))
        for b, s in outbox_states(catalog)
        if s["event"] == "confirmed" and int(str(s["block_time_s"])) >= since_s
    }
    series_of = {
        str(r["record_id"]): (str(r["venue"]), str(r["symbol"]))
        for r in tables.records_table(catalog).read().to_pylist()
    }
    latencies: list[int] = []
    series: set[tuple[str, str]] = set()
    for leaf in tables.leaves_table(catalog).read().to_pylist():
        block_time = confirmed.get(str(leaf["batch_root"]))
        if block_time is None:
            continue
        latencies.append(block_time - int(str(leaf["bar_close_time_ns"])) // SECOND_NS)
        series.add(series_of.get(str(leaf["record_id"]), ("", "")))

    window = (max(confirmed.values()) - min(confirmed.values())) if confirmed else 0
    ordered = sorted(latencies)
    meets = (
        len(ordered) >= CRITERION_RECORDS
        and len(series) >= CRITERION_SERIES
        and window >= CRITERION_WINDOW_S
    )
    verdict = (
        f"meets the success criterion ({CRITERION_RECORDS}+ records, {CRITERION_SERIES}+ series, "
        f"{CRITERION_WINDOW_S // 3600}+ h)"
        if meets
        else f"insufficient: {len(ordered)} records, {len(series)} series, {window} s; "
        f"the criterion is {CRITERION_RECORDS}+ records, {CRITERION_SERIES}+ series and "
        f"{CRITERION_WINDOW_S} s"
    )
    return LatencyReport(
        sample=len(ordered),
        series=len(series),
        window_s=window,
        latencies_s=latencies,
        median_s=statistics.median_low(ordered) if ordered else 0,
        p95_s=ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else 0,
        max_s=ordered[-1] if ordered else 0,
        meets_criterion=meets,
        verdict=verdict,
    )
