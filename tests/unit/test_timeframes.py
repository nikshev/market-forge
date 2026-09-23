# @trace: REQ-WP-073
import pytest

from channelflow.timeframes import (
    TIMEFRAMES,
    CalendarPeriod,
    Timeframe,
    UnknownTimeframe,
    parse,
    parse_list,
)


class TestTimeframeCreation:
    @pytest.mark.trace("REQ-WP-073")
    def test_timeframe_requires_positive_ns(self):
        with pytest.raises(ValueError):
            Timeframe("1m", 0, 0)
        with pytest.raises(ValueError):
            Timeframe("1m", -60_000_000_000, 0)

    @pytest.mark.trace("REQ-WP-073")
    def test_timeframe_origin_within_bounds(self):
        with pytest.raises(ValueError):
            Timeframe("1m", 60_000_000_000, -1)
        with pytest.raises(ValueError):
            Timeframe("1m", 60_000_000_000, 60_000_000_000)

    @pytest.mark.trace("REQ-WP-073")
    def test_weekly_with_origin_equal_ns_is_refused(self):
        # origin_ns == ns is the same alignment spelled confusingly
        with pytest.raises(ValueError):
            Timeframe("1w", 604_800_000_000_000, 604_800_000_000_000)


class TestTimeframeConstants:
    @pytest.mark.trace("REQ-WP-073")
    def test_token_matches_key(self):
        for key, tf in TIMEFRAMES.items():
            assert tf.token == key

    @pytest.mark.trace("REQ-WP-073")
    def test_ns_multiple_of_one_minute(self):
        one_minute_ns = TIMEFRAMES["1m"].ns
        for key, tf in TIMEFRAMES.items():
            assert tf.ns % one_minute_ns == 0, f"{key}: {tf.ns} not multiple of {one_minute_ns}"


class TestWindowStart:
    @pytest.mark.trace("REQ-WP-073")
    def test_weekly_containing_thursday_opens_monday(self):
        # 2026-09-17T09:15:00Z is a Thursday -> window should open Monday 2026-09-14
        thursday_ns = 1_789_636_500_000_000_000
        w = TIMEFRAMES["1w"]
        start = w.window_start(thursday_ns)
        assert start == 1_789_344_000_000_000_000  # 2026-09-14T00:00:00Z

        # 2026-09-13T23:59:59Z is a Sunday -> window should open Monday 2026-09-07
        sunday_ns = 1_789_280_799_000_000_000
        start = w.window_start(sunday_ns)
        assert start == 1_788_739_200_000_000_000  # 2026-09-07T00:00:00Z

    @pytest.mark.trace("REQ-WP-073")
    def test_window_start_idempotent(self):
        for tf in TIMEFRAMES.values():
            for t in [
                0,
                1_000_000_000,
                60_000_000_000,
                3_600_000_000_000,
                86_400_000_000_000,
                604_800_000_000_000,
            ]:
                start1 = tf.window_start(t)
                start2 = tf.window_start(start1)
                assert start1 == start2, f"{tf.token}: {t} -> {start1} != {start2}"

    @pytest.mark.trace("REQ-WP-073")
    def test_weekly_floor_division_not_truncation(self):
        # At t=0, floor division with origin gives -259_200_000_000_000 (1969-12-29, Monday)
        # Math.trunc would give 0 (Thursday 1970-01-01)
        w = TIMEFRAMES["1w"]
        start = w.window_start(0)
        assert start == -259_200_000_000_000


class TestParse:
    @pytest.mark.trace("REQ-WP-073")
    def test_parse_unknown_raises(self):
        with pytest.raises(UnknownTimeframe) as exc:
            parse("99m")
        assert "99m" in str(exc.value)

    @pytest.mark.trace("REQ-WP-073")
    def test_parse_1m_raises_calendar_period(self):
        with pytest.raises(CalendarPeriod) as exc:
            parse("1M")
        assert "month" in str(exc.value).lower() or "calendar" in str(exc.value).lower()

    @pytest.mark.trace("REQ-WP-073")
    def test_parse_other_calendar_periods_raise_too(self):
        # FR-008: `1M` *or any calendar-defined period*. A year has the same
        # leap-day problem a month has.
        for token in ("1y", "3M", "1Y"):
            with pytest.raises(CalendarPeriod):
                parse(token)

    @pytest.mark.trace("REQ-WP-073")
    def test_a_typo_is_unknown_not_a_calendar_period(self):
        with pytest.raises(UnknownTimeframe):
            parse("1x")
        with pytest.raises(UnknownTimeframe):
            parse("5M ")  # trailing space is trimmed by parse_list, not by parse

    @pytest.mark.trace("REQ-WP-073")
    def test_parse_list_empty_raises(self):
        with pytest.raises(ValueError):
            parse_list("")
        with pytest.raises(ValueError):
            parse_list(" , ")

    @pytest.mark.trace("REQ-WP-073")
    def test_parse_list_dedup_and_sort(self):
        result = parse_list("1h,5m,1h")
        assert tuple(tf.token for tf in result) == ("5m", "1h")

        result = parse_list("1d,1w,5m,1h")
        assert tuple(tf.token for tf in result) == ("5m", "1h", "1d", "1w")
