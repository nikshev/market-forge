"""No unfinalized higher-timeframe close reaches a lower-timeframe consumer (REQ-NRT-UPSAMPLE).

PRD §13A.17: "Do not upsample a higher-timeframe future close into lower-timeframe features before
that higher-timeframe bar is finalized."

`resample` already refused a closed window that was short of minutes, and a test said so. Running it
showed the claim was about a function and the requirement is about a seam: a window whose minutes
were four distinct plus one repeated -- minute four missing -- was folded into a bar, and so was a
window containing a bar that was not final. Both are *latent* on the deployment (55,546 one-minute
rows, all keys distinct; the table refuses unfinalized rows on write), which is exactly why nothing
saw them: what kept them out was another module's behaviour.

The three stories are the three halves of the seam: what `resample` will fold (US1), what the table
will hand out for an instant inside an open window (US2), and what any read as of `t` can contain
(US3). Tests that pass today by design say so; the mutation sweep (`resample_leak.toml`) is the
fourth story, and the part that makes a hard-gated constraint something that has seen its violation.
"""

from __future__ import annotations

import pytest

from channelflow.bars.models import Bar
from channelflow.lakehouse import Catalog
from channelflow.pipeline.resample import resample
from channelflow.tables import bars as bars_table
from channelflow.timeframes import TIMEFRAMES, Timeframe
from channelflow.timeframes import parse as parse_timeframe

from .test_resample import make_bar

MINUTE = 60_000_000_000
FIVE = parse_timeframe("5m")
ONE = parse_timeframe("1m")
LONG_AFTER = 10**19  # a now_ns that closes every window in these fixtures


def _window(minutes: list[int], *, not_final: frozenset[int] = frozenset()) -> list[Bar]:
    return [make_bar(m * MINUTE, is_final=m not in not_final) for m in minutes]


def _fold(bars: list[Bar], *, now_ns: int = LONG_AFTER):  # type: ignore[no-untyped-def]
    return resample(bars, target=FIVE, source_timeframe=ONE, now_ns=now_ns)


# --- User Story 1: a window is a bar only if every minute is there, once, and final -----------


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_complete_window_of_final_minutes_is_a_bar() -> None:
    """The control, green before the change: five distinct final minutes, one bar."""
    result = _fold(_window([0, 1, 2, 3, 4]))

    assert len(result.bars) == 1 and result.refusals == ()


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_repeated_minute_does_not_stand_in_for_a_missing_one() -> None:
    """Minutes 0, 1, 2, 3 and 3 again -- minute 4 absent. Five bars, four distinct minutes. Counting
    says complete; identifying says not. Fails today: one bar, no refusal."""
    result = _fold(_window([0, 1, 2, 3, 3]))

    assert result.bars == (), "a bar computed from four of five minutes"
    assert len(result.refusals) == 1
    reason = result.refusals[0].reason
    assert result.refusals[0].open_time_ns == 0
    assert "missing" in reason and str(4 * MINUTE) in reason, reason
    assert "duplicated" in reason and str(3 * MINUTE) in reason, reason


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_window_whose_minutes_are_all_there_but_one_repeated_is_refused() -> None:
    """Six bars for five minutes: every minute present, one twice. Which copy is right is not known,
    so the window is refused (FR-001: each minute exactly once). Passes today only because six is not
    five; named so the case is not lost when the check changes from counting to identifying."""
    result = _fold(_window([0, 1, 2, 3, 4, 4]))

    assert result.bars == () and len(result.refusals) == 1
    assert "duplicated" in result.refusals[0].reason


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_window_with_a_source_bar_that_is_not_final_is_refused_and_says_which() -> None:
    """All five minutes present, minute two still able to change. Fails today: one bar, no refusal --
    `resample` never reads `is_final`."""
    result = _fold(_window([0, 1, 2, 3, 4], not_final=frozenset({2})))

    assert result.bars == ()
    assert len(result.refusals) == 1
    reason = result.refusals[0].reason
    assert "not final" in reason and str(2 * MINUTE) in reason, reason


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_missing_minute_is_still_refused_with_the_window_and_the_count() -> None:
    """The property the existing test covers, kept: green before the change."""
    result = _fold(_window([0, 1, 2, 4]))

    assert result.bars == () and len(result.refusals) == 1
    refusal = result.refusals[0]
    assert refusal.open_time_ns == 0 and refusal.expected == 5
    assert "4 of 5" in refusal.reason


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_window_still_open_yields_neither_a_bar_nor_a_refusal() -> None:
    """Green before the change (FR-003): nothing about an open window is wrong yet."""
    result = _fold(_window([0, 1, 2]), now_ns=3 * MINUTE)

    assert result.bars == () and result.refusals == ()


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_of_the_five_window_shapes_exactly_one_is_a_bar_and_exactly_three_are_refused() -> None:
    """SC-001, across the shapes at once: complete, repeated-with-a-gap, one not final, one missing,
    open. Today three produce a bar."""
    shapes = {
        "complete": (_window([0, 1, 2, 3, 4]), LONG_AFTER),
        "repeated with a gap": (_window([0, 1, 2, 3, 3]), LONG_AFTER),
        "one not final": (_window([0, 1, 2, 3, 4], not_final=frozenset({1})), LONG_AFTER),
        "one missing": (_window([0, 1, 2, 4]), LONG_AFTER),
        "open": (_window([0, 1, 2]), 3 * MINUTE),
    }
    results = {name: _fold(bars, now_ns=now) for name, (bars, now) in shapes.items()}

    assert [n for n, r in results.items() if r.bars] == ["complete"]
    assert sorted(n for n, r in results.items() if r.refusals) == [
        "one missing",
        "one not final",
        "repeated with a gap",
    ]


# --- User Story 2: nothing inside an open window can be read ----------------------------------


def _stored(catalog: Catalog, bars: list[Bar]):  # type: ignore[no-untyped-def]
    table = bars_table.table_for(catalog)
    bars_table.write_bars(table, bars)
    return table


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_a_bar_cannot_be_read_as_of_any_instant_inside_its_window(catalog: Catalog) -> None:
    """Asked, not inspected: a resampled five-minute bar is written to a real table and the series is
    read as of every instant from the window's open up to its last nanosecond. A regression guard,
    green before the change -- the as-of read already filters on `close_time_ns`; nothing tested it
    with a resampled bar."""
    folded = _fold(_window([0, 1, 2, 3, 4])).bars
    table = _stored(catalog, list(folded))
    five = FIVE.ns
    instants = [0, 1, MINUTE, 2 * MINUTE, 4 * MINUTE, five - MINUTE, five - 1]

    for instant in instants:
        got = bars_table.read_bars(table, timeframe_ns=five, as_of_ns=instant)
        assert got == [], f"the bar was readable as of {instant}, before it closed at {five}"


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_the_bar_is_readable_the_instant_its_window_closes(catalog: Catalog) -> None:
    """The other side of the boundary, so the test above is not satisfied by a table that never
    returns anything. Green before the change."""
    folded = _fold(_window([0, 1, 2, 3, 4])).bars
    table = _stored(catalog, list(folded))

    got = bars_table.read_bars(table, timeframe_ns=FIVE.ns, as_of_ns=FIVE.ns)

    assert [b.open_time_ns for b in got] == [0]


# --- User Story 3: a read as of t never holds a bar that closes after t ------------------------

DAY_START_NS = 1_790_899_200 * 1_000_000_000  # 2026-10-02T00:00:00Z, a window start at every size
DAY_MINUTES = 24 * 60


def _a_day_of_minutes() -> list[Bar]:
    return [make_bar(DAY_START_NS + i * MINUTE, close=str(100 + i % 7)) for i in range(DAY_MINUTES)]


def _instants() -> list[int]:
    """Every seventh minute, and the instant before, at and after every window boundary of every
    configured timeframe up to a day -- the places a leak would show."""
    points = {DAY_START_NS + i * MINUTE for i in range(0, DAY_MINUTES, 7)}
    for timeframe in TIMEFRAMES.values():
        if timeframe.ns > DAY_MINUTES * MINUTE:
            continue
        for start in range(DAY_START_NS, DAY_START_NS + DAY_MINUTES * MINUTE, timeframe.ns):
            points.update({start + timeframe.ns - 1, start + timeframe.ns, start + timeframe.ns + 1})
    return sorted(p for p in points if DAY_START_NS <= p <= DAY_START_NS + DAY_MINUTES * MINUTE)


def _store_every_timeframe(catalog: Catalog):  # type: ignore[no-untyped-def]
    source = _a_day_of_minutes()
    table = bars_table.table_for(catalog)
    bars_table.write_bars(table, source)
    now = DAY_START_NS + DAY_MINUTES * MINUTE
    for target in TIMEFRAMES.values():
        if target.ns <= ONE.ns or target.ns > DAY_MINUTES * MINUTE:
            continue
        folded = resample(
            source, target=target, source_timeframe=ONE, now_ns=now
        ).bars
        if folded:
            bars_table.write_bars(table, list(folded))
    return table


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_no_read_as_of_t_contains_a_bar_that_closes_after_t(catalog: Catalog) -> None:
    """FR-005 over a day of source bars and every configured timeframe: at each chosen `t`, every
    bar of every timeframe returned closed at or before `t`. A guard, green before the change."""
    table = _store_every_timeframe(catalog)
    instants = _instants()
    assert len(instants) > 100, "too few instants to say anything"

    for t in instants:
        late = [b for b in bars_table.read_bars(table, as_of_ns=t) if b.close_time_ns > t]
        assert late == [], f"as of {t}: {[(b.timeframe_ns, b.open_time_ns) for b in late]}"


@pytest.mark.trace("REQ-NRT-UPSAMPLE")
def test_the_property_is_the_as_of_reads_and_not_an_accident_of_the_fixture(
    catalog: Catalog,
) -> None:
    """A reader that ignores the as-of argument *does* meet bars from the future -- so the check
    above can fail, and is a statement about the read and not about the data."""
    table = _store_every_timeframe(catalog)
    everything = bars_table.read_bars(table)

    leaked = [
        (t, b.timeframe_ns)
        for t in _instants()
        for b in everything
        if b.close_time_ns > t and b.timeframe_ns != ONE.ns
    ]

    assert leaked, "reading without `as_of_ns` produced no future bar; the fixture proves nothing"
