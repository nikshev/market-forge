"""Resample one-minute bars into higher configured timeframes.

# @trace: REQ-WP-073
# @trace: REQ-NRT-UPSAMPLE

The fold is pure and takes no clock. `resample` groups by window and refuses
what it cannot honestly build; `resample_main` is the process that runs it.

Every target is built from the source directly. No target is built from another
target, because chaining would compound both arithmetic error and
incompleteness, and the level that refused would not be the level that was
wrong ([[REQ-WP-073]]).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext

from channelflow.bars.models import Bar
from channelflow.timeframes import Timeframe


@dataclass(frozen=True)
class Refusal:
    """Why a window produced no bar.

    Carried as a value rather than logged and discarded: FR-005 requires it to
    reach the caller, and a pass that silently dropped an incomplete window
    would look from the outside exactly like a pass that had nothing to do.
    """

    open_time_ns: int
    expected: int
    present: int
    reason: str


#: How many open times a refusal names before it says how many more there were. A day-long window
#: short of a thousand minutes would otherwise put a thousand numbers on a line the job prints on
#: every pass, which is the log volume [[REQ-WP-078]] spent a change removing.
NAMED_IN_A_REFUSAL = 5


def _named(open_times: Sequence[int]) -> str:
    shown = ", ".join(str(t) for t in open_times[:NAMED_IN_A_REFUSAL])
    extra = len(open_times) - NAMED_IN_A_REFUSAL
    return f"[{shown}, +{extra} more]" if extra > 0 else f"[{shown}]"


def _judgement(
    window: Sequence[Bar], *, start: int, expected: int, step: int
) -> tuple[int, list[str]]:
    """What is wrong with a closed window, by *identifying* its minutes rather than counting them.

    [[REQ-NRT-UPSAMPLE]]: five bars is not five minutes. Minutes 0, 1, 2, 3 and 3 again number five
    and are four, and counting called that complete and folded a bar from four-fifths of a window.
    A bar that is not final may still change, so a window holding one is not the window it will be.

    Returns how many distinct expected minutes are present and a description of each fault, empty
    when the window is sound.
    """
    wanted = [start + k * step for k in range(expected)]
    held: dict[int, int] = {}
    for bar in window:
        held[bar.open_time_ns] = held.get(bar.open_time_ns, 0) + 1
    missing = [t for t in wanted if t not in held]
    duplicated = [t for t in wanted if held.get(t, 0) > 1]
    not_final = sorted({bar.open_time_ns for bar in window if not bar.is_final})

    faults: list[str] = []
    if missing:
        faults.append(f"missing {_named(missing)}")
    if duplicated:
        faults.append(f"duplicated {_named(duplicated)}")
    if not_final:
        faults.append(f"not final {_named(not_final)}")
    return expected - len(missing), faults


@dataclass(frozen=True)
class ResampleResult:
    """What `resample` computed. Pure: it knows nothing about a table."""

    bars: tuple[Bar, ...]
    refusals: tuple[Refusal, ...]
    skipped: int


@dataclass(frozen=True)
class ResampleReport:
    """What one pass did, for one `(venue, symbol, timeframe)`.

    Distinct from `ResampleResult`, and named closely enough to be worth
    stating why: the result is what the pure function computed, the report is
    what the process actually committed and printed. A pass can compute ten
    bars and fail to append them, and one type cannot honestly carry both.
    """

    venue: str
    symbol: str
    timeframe: Timeframe
    written: int
    skipped: int
    refusals: tuple[Refusal, ...]

    @property
    def line(self) -> str:
        parts = [
            f"{self.venue} {self.symbol} {self.timeframe.token}:",
            f"written={self.written}",
            f"skipped={self.skipped}",
        ]
        if self.refusals:
            parts.append(f"refused={len(self.refusals)}")
        return " ".join(parts)


def report_for(
    result: ResampleResult,
    *,
    venue: str,
    symbol: str,
    timeframe: Timeframe,
    written: int,
) -> ResampleReport:
    """Pair what `resample` computed with what the pass actually committed.

    `written` is a parameter rather than `len(result.bars)` on purpose: an
    append that raised leaves the result holding bars that are not on the
    table, and a report deriving its count from the computation would claim
    rows that do not exist.
    """
    return ResampleReport(
        venue=venue,
        symbol=symbol,
        timeframe=timeframe,
        written=written,
        skipped=result.skipped,
        refusals=result.refusals,
    )


def fold(
    window_bars: Sequence[Bar],
    *,
    venue: str,
    symbol: str,
    target: Timeframe,
) -> Bar:
    """Aggregate a complete window's source bars into one bar at `target`.

    The input is expected in `open_time_ns` order; the caller groups and
    orders it. Every field follows `BarBuilder._to_bar` so a bar produced here
    and a bar produced by the builder for the same window agree.
    """
    ordered = sorted(window_bars, key=lambda bar: bar.open_time_ns)
    first = ordered[0]
    last = ordered[-1]

    high_bar = ordered[0]
    low_bar = ordered[0]
    for bar in ordered[1:]:
        if bar.high > high_bar.high:
            high_bar = bar
        if bar.low < low_bar.low:
            low_bar = bar

    volume_base = sum((bar.volume_base for bar in ordered), Decimal(0))
    volume_quote = sum((bar.volume_quote for bar in ordered), Decimal(0))
    aggressive_buy_base = sum((bar.aggressive_buy_base for bar in ordered), Decimal(0))
    aggressive_sell_base = sum((bar.aggressive_sell_base for bar in ordered), Decimal(0))
    trade_count = sum(bar.trade_count for bar in ordered)

    # Decimal's default context rounds at 28 significant digits, which silently
    # truncates a venue price carrying more. The builder widens the context to
    # 60 for exactly this reason (builder.py:167-176); a resampled bar must
    # agree with a builder-produced bar of the same window.
    with localcontext() as ctx:
        ctx.prec = 60
        vwap = volume_quote / volume_base if volume_base > 0 else last.close

    return Bar(
        venue=venue,
        symbol=symbol,
        timeframe_ns=target.ns,
        open_time_ns=first.open_time_ns,
        close_time_ns=first.open_time_ns + target.ns,
        open=first.open,
        high=high_bar.high,
        low=low_bar.low,
        close=last.close,
        volume_base=volume_base,
        volume_quote=volume_quote,
        trade_count=trade_count,
        aggressive_buy_base=aggressive_buy_base,
        aggressive_sell_base=aggressive_sell_base,
        delta_base=aggressive_buy_base - aggressive_sell_base,
        vwap=vwap,
        high_time_ns=high_bar.high_time_ns,
        low_time_ns=low_bar.low_time_ns,
        first_trade_id=first.first_trade_id,
        last_trade_id=last.last_trade_id,
        is_final=True,
    )


def resample(
    source: Iterable[Bar],
    *,
    target: Timeframe,
    source_timeframe: Timeframe,
    already_present: frozenset[int] = frozenset(),
    now_ns: int,
) -> ResampleResult:
    """Group `source` bars by `target`'s windows; emit complete, closed ones.

    A window that is closed and incomplete yields a `Refusal` rather than a bar
    computed from whatever minutes happened to arrive — the condition
    [[REQ-NRT-UPSAMPLE]] states and tests.

    A window still in progress yields neither a bar nor a refusal: nothing
    about it is wrong yet, and refusing it would report a problem on every pass
    for the window that is supposed to be open.
    """
    if target.ns % source_timeframe.ns != 0:
        raise ValueError(
            f"target {target.token} ({target.ns}ns) is not a whole multiple of "
            f"source {source_timeframe.token} ({source_timeframe.ns}ns); "
            "such windows cannot tile the source"
        )

    expected = target.ns // source_timeframe.ns

    windows: dict[int, list[Bar]] = {}
    for bar in source:
        start = target.window_start(bar.open_time_ns)
        windows.setdefault(start, []).append(bar)

    bars: list[Bar] = []
    refusals: list[Refusal] = []
    skipped = 0
    for start in sorted(windows):
        close = start + target.ns
        if close > now_ns:
            continue
        window = windows[start]
        if start in already_present:
            skipped += 1
            continue
        present, faults = _judgement(
            window, start=start, expected=expected, step=source_timeframe.ns
        )
        if faults:
            refusals.append(
                Refusal(
                    open_time_ns=start,
                    expected=expected,
                    present=present,
                    reason=(
                        f"window {start} at {target.token} has {present} of "
                        f"{expected} source {source_timeframe.token} bars; " + "; ".join(faults)
                    ),
                )
            )
            continue
        bars.append(fold(window, venue=window[0].venue, symbol=window[0].symbol, target=target))

    return ResampleResult(bars=tuple(bars), refusals=tuple(refusals), skipped=skipped)
