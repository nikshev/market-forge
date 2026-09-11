"""PRD §29.5's `feature_snapshots`, and §29's `markets` and scored setups.

# @trace: REQ-STORE-002

    ## 29.5. `feature_snapshots`
    Prefer wide table for stable production feature set plus optional long table
    for experimental registry.

The long form is what is built. §29.5 prefers a wide table for a *stable*
production feature set, and there is not one: `exposed_feature_names()` grows
whenever a producing module is added, and a wide table would need a schema change
— and therefore a new schema fingerprint, and therefore a new dataset identity —
every time. The long form takes a new feature without touching the schema, which
is exactly why §29.5 offers it alongside.

Three tables live here because each is small and they are read together by the
same caller: the feature points, the market list, and the latest score per
market.
"""

from __future__ import annotations

import hashlib
import struct
from decimal import Decimal

from channelflow.domain import Instrument
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.scoring import Group, GroupContribution, SignalScore
from channelflow.tables.rows import (
    as_decimal,
    as_float,
    as_float_map,
    as_int,
    as_str,
    as_str_tuple,
)

FEATURES_TABLE_NAME = "feature_snapshots"
MARKETS_TABLE_NAME = "markets"
SCORES_TABLE_NAME = "setup_scores"
CONTRIBUTIONS_TABLE_NAME = "score_contributions"

#: PRD §29.5's long form: one row per feature per instant, so a new feature is a
#: new row rather than a new column.
FEATURES_SCHEMA = Schema(
    columns=(
        Column(name="at_ns", type="timestamp_ns"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="feature_name", type="string"),
        Column(name="value", type="float64"),
    ),
    event_time_column="at_ns",
)

#: A market list has no event time: it is configuration, not observation. The
#: schema says so by declaring none, which means a point-in-time read of it is
#: refused rather than answered -- see PRD §41 rule 7 on point-in-time listing
#: history, which is a different and harder question than this table answers.
MARKETS_SCHEMA = Schema(
    columns=(
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="market_type", type="string"),
        # [[REQ-WP-021]]'s rules. Decimal rather than float: a tick size that
        # went through binary floating point is not the venue's tick size.
        Column(name="base_asset", type="string"),
        Column(name="quote_asset", type="string"),
        Column(name="tick_size", type="decimal"),
        Column(name="step_size", type="decimal"),
        Column(name="min_notional", type="decimal"),
        # An instrument with no contracts stores an empty string rather than a
        # zero, because absent and zero must not read alike -- and the plane has
        # no null.
        Column(name="contract_size", type="string"),
        Column(name="status", type="string"),
    )
)

#: The latest score per market, appended. Reading takes the newest row per
#: market rather than overwriting one, because the plane is append-only and a
#: score history is worth more than a mutable cell.
SCORES_SCHEMA = Schema(
    columns=(
        Column(name="as_of_ns", type="timestamp_ns"),
        Column(name="score_id", type="string"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="raw", type="float64"),
        Column(name="final", type="float64"),
        Column(name="data_quality", type="float64"),
        Column(name="confidence", type="float64"),
        Column(name="missing_groups", type="string_list"),
        Column(name="feature_snapshot", type="float_map"),
        Column(name="model_version", type="string"),
        Column(name="liquidity_factor", type="float64"),
        Column(name="novelty_factor", type="float64"),
    ),
    event_time_column="as_of_ns",
)

#: A score's own identity, so its contributions join to *it* rather than to
#: whatever else was scored at the same instant. Two scores tie on `as_of_ns`
#: whenever the caller does not supply one, and a join on the instant then gives
#: a score every group any of them had -- a score that does not add up, read
#: back from rows that are each correct.
#:
#: Content-derived rather than random: the same score written twice is the same
#: score, and a random id would make a re-run of a backfill look like new data.


def score_id(
    *, venue: str, symbol: str, as_of_ns: int, model_version: str, score: SignalScore
) -> str:
    digest = hashlib.sha256()
    parts = [
        venue.encode(),
        symbol.encode(),
        str(as_of_ns).encode(),
        model_version.encode(),
        repr((score.raw, score.final, score.data_quality, score.confidence)).encode(),
        repr(sorted((str(c.group), c.value, c.factors) for c in score.contributions)).encode(),
        repr(sorted(str(group) for group in score.missing)).encode(),
    ]
    for part in parts:
        digest.update(struct.pack("<I", len(part)))
        digest.update(part)
    return digest.hexdigest()


#: One row per §22.1 group behind a score. A child table rather than three
#: parallel lists: the factor names are themselves a list, and a list of lists
#: on a parent row is a shape nothing can query without unnesting twice.
#:
#: There is no `cap` column. A group's cap is `GROUP_CAPS[group]` -- a §22.1
#: constant, not a property of one contribution -- and storing it would create a
#: second source of truth that a reader could believe over the constant. The six
#: caps sum to 100 by design, and a row claiming otherwise would break that
#: silently.
CONTRIBUTIONS_SCHEMA = Schema(
    columns=(
        Column(name="as_of_ns", type="timestamp_ns"),
        Column(name="score_id", type="string"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="group_name", type="string"),
        Column(name="value", type="float64"),
        Column(name="factors", type="string_list"),
    ),
    event_time_column="as_of_ns",
)


def features_table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=FEATURES_TABLE_NAME, schema=FEATURES_SCHEMA, catalog=catalog)


def markets_table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=MARKETS_TABLE_NAME, schema=MARKETS_SCHEMA, catalog=catalog)


def scores_table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=SCORES_TABLE_NAME, schema=SCORES_SCHEMA, catalog=catalog)


def contributions_table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=CONTRIBUTIONS_TABLE_NAME, schema=CONTRIBUTIONS_SCHEMA, catalog=catalog)


def market_row(instrument: Instrument) -> dict[str, object]:
    """One instrument as a row of the markets table."""
    return {
        "venue": instrument.venue,
        "symbol": instrument.symbol,
        "market_type": instrument.market_type,
        "base_asset": instrument.base_asset,
        "quote_asset": instrument.quote_asset,
        "tick_size": instrument.tick_size,
        "step_size": instrument.step_size,
        "min_notional": instrument.min_notional,
        "contract_size": "" if instrument.contract_size is None else str(instrument.contract_size),
        "status": instrument.status,
    }


def instrument_from_row(row: dict[str, object]) -> Instrument | None:
    """The instrument a market row describes, or nothing when it describes none.

    A row written before [[REQ-WP-021]] -- or by `add_market` without rules --
    carries empty strings, and an instrument reconstructed from those would
    report a tick size of zero. Absent is the honest answer, and `Instrument`
    refuses the alternative anyway.
    """
    # Numerically, not by truthiness: a decimal column reads back as a string on
    # some paths, and `not "0"` is False -- so a market with no rules would have
    # been reconstructed as an instrument and refused on its empty base asset.
    # Found by four API tests going red.
    if as_decimal(row, "tick_size") <= 0:
        return None
    contract = as_str(row, "contract_size")
    return Instrument(
        venue=as_str(row, "venue"),
        symbol=as_str(row, "symbol"),
        market_type=as_str(row, "market_type"),
        base_asset=as_str(row, "base_asset"),
        quote_asset=as_str(row, "quote_asset"),
        tick_size=as_decimal(row, "tick_size"),
        step_size=as_decimal(row, "step_size"),
        min_notional=as_decimal(row, "min_notional"),
        contract_size=Decimal(contract) if contract else None,
        status=as_str(row, "status"),
    )


def feature_rows(
    *, venue: str, symbol: str, timeframe_ns: int, at_ns: int, values: dict[str, float]
) -> list[dict[str, object]]:
    """One instant's features, in the long form, with the names sorted.

    Sorted so a snapshot written twice from the same mapping produces the same
    rows in the same order and therefore the same content hash -- a dataset
    identity that depended on a dict's insertion order would change for a
    snapshot that did not.
    """
    return [
        {
            "at_ns": at_ns,
            "venue": venue,
            "symbol": symbol,
            "timeframe_ns": timeframe_ns,
            "feature_name": name,
            "value": values[name],
        }
        for name in sorted(values)
    ]


def score_rows(
    *,
    venue: str,
    symbol: str,
    as_of_ns: int,
    score: SignalScore,
    feature_snapshot: dict[str, float],
    model_version: str,
    liquidity_factor: float,
    novelty_factor: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    identity = score_id(
        venue=venue,
        symbol=symbol,
        as_of_ns=as_of_ns,
        model_version=model_version,
        score=score,
    )
    core: dict[str, object] = {
        "as_of_ns": as_of_ns,
        "score_id": identity,
        "venue": venue,
        "symbol": symbol,
        "raw": score.raw,
        "final": score.final,
        "data_quality": score.data_quality,
        "confidence": score.confidence,
        "missing_groups": [str(group) for group in score.missing],
        "feature_snapshot": dict(feature_snapshot),
        "model_version": model_version,
        "liquidity_factor": liquidity_factor,
        "novelty_factor": novelty_factor,
    }
    contributions = [
        {
            "as_of_ns": as_of_ns,
            "score_id": identity,
            "venue": venue,
            "symbol": symbol,
            "group_name": str(contribution.group),
            "value": contribution.value,
            "factors": list(contribution.factors),
        }
        for contribution in score.contributions
    ]
    return core, contributions


def score_from_rows(core: dict[str, object], contributions: list[dict[str, object]]) -> SignalScore:
    """A score back from its two tables.

    `GroupContribution` refuses a value above its cap rather than clipping it,
    so a row that stored an impossible pair raises here rather than reading back
    as a perfect group -- which is the behaviour its own docstring exists for.
    """
    return SignalScore(
        raw=as_float(core, "raw"),
        final=as_float(core, "final"),
        data_quality=as_float(core, "data_quality"),
        confidence=as_float(core, "confidence"),
        contributions=tuple(
            GroupContribution(
                group=Group(as_str(row, "group_name")),
                value=as_float(row, "value"),
                factors=as_str_tuple(row, "factors"),
            )
            for row in sorted(contributions, key=lambda row: as_str(row, "group_name"))
        ),
        missing=tuple(Group(name) for name in as_str_tuple(core, "missing_groups")),
    )


def snapshot_of(core: dict[str, object]) -> dict[str, float]:
    return as_float_map(core, "feature_snapshot")


def newest_score_row(
    rows: list[dict[str, object]], *, venue: str, symbol: str
) -> dict[str, object] | None:
    """The latest score row for one market, or nothing.

    Nothing rather than an empty score: a market nobody has scored and a market
    that scored zero are different facts, and the API's caller distinguishes
    them.
    """
    matched = [row for row in rows if row["venue"] == venue and row["symbol"] == symbol]
    if not matched:
        return None
    # The last of the newest, not the first. Scores share an `as_of_ns` whenever
    # the caller does not supply one, and `max` returns the first maximal
    # element -- which would pin the reader to the oldest score of a tied group
    # and make a rewrite invisible. The plane is append-only, so the last row
    # written is the latest thing anyone said.
    newest = max(as_int(row, "as_of_ns") for row in matched)
    return [row for row in matched if as_int(row, "as_of_ns") == newest][-1]
