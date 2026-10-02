"""Moving the archive objects already written to the layout that names a symbol (REQ-WP-078).

# @trace: REQ-WP-078

24,825 objects, 487 MB, under keys no reader finds or that name no symbol. Each holds
frames of one symbol -- because the process that wrote it was one symbol -- so each can
be attributed from its own contents. What cannot be done is anything irreversible on a
guess, so the cases that matter here are the refusals and the interruptions: a copy that
came out wrong, a delete that never happened, a destination that already holds something
else, an object that names two symbols.

The store is `FakeS3`, whose ETags derive from content, so "verified" is a comparison.
"""

from __future__ import annotations

import gzip
import json

import pytest

from channelflow.pipeline import archive_rekey as rk

from .fake_s3 import FakeS3

B = "bucket"
DAY = "2026/09/20"


def _body(frames: list[str]) -> bytes:
    lines = [
        json.dumps(
            {"received_at_ns": 1_790_000_000_000_000_000 + i, "frame": f}, separators=(",", ":")
        )
        for i, f in enumerate(frames)
    ]
    return gzip.compress("\n".join(lines).encode())


def _binance(symbol: str) -> str:
    return json.dumps({"stream": f"{symbol.lower()}@aggTrade", "data": {"s": symbol}})


def _bybit(symbol: str) -> str:
    return json.dumps({"topic": f"publicTrade.{symbol}", "type": "snapshot", "data": []})


def _okx(inst: str) -> str:
    return json.dumps({"arg": {"channel": "trades", "instId": inst}, "data": [{"px": "1"}]})


def _layout_a(venue: str, hhmm: str, day: str = DAY) -> str:
    return f"raw/cex/{venue}/{day}/{hhmm}.jsonl.gz"


def _layout_b(venue: str, hhmm: str, day: str = DAY) -> str:
    return f"{venue}/raw/cex/{venue}/{day}/{hhmm}.jsonl.gz"


def _new(venue: str, symbol: str, hhmm: str, day: str = DAY) -> str:
    return f"raw/cex/{venue}/{symbol}/{day}/{hhmm}.jsonl.gz"


def _store(**objects: bytes) -> FakeS3:
    s3 = FakeS3()
    for key, body in objects.items():
        s3.put_object(Bucket=B, Key=key.replace("__", "/"), Body=body)
    return s3


def _seed(s3: FakeS3, key: str, frames: list[str]) -> bytes:
    body = _body(frames)
    s3.put_object(Bucket=B, Key=key, Body=body)
    return body


# --- key parsing --------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("key", "venue", "layout"),
    [
        (_layout_a("binance", "1200"), "binance", "A"),
        (_layout_b("bybit", "1059", "2026/10/02"), "bybit", "B"),
        (_new("okx", "BTC-USDT-SWAP", "0001"), "okx", "C"),
    ],
)
def test_the_three_layouts_are_recognised(key: str, venue: str, layout: str) -> None:
    parsed = rk.parse_key(key)

    assert parsed is not None
    assert (parsed.venue, parsed.layout) == (venue, layout)


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    "key",
    [
        "warehouse/bars/data/x.parquet",
        "raw/cex/binance/notes.txt",
        "raw/cex/binance/2026/09/20/12.jsonl.gz",
        "binance/raw/cex/bybit/2026/09/20/1200.jsonl.gz",  # the venue in two minds
    ],
)
def test_a_key_that_matches_no_layout_is_not_one(key: str) -> None:
    assert rk.parse_key(key) is None


# --- attribution --------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("venue", "frame", "symbol"),
    [
        ("binance", _binance("BTCUSDT"), "BTCUSDT"),  # the stream label is lower case
        ("bybit", _bybit("ETHUSDT"), "ETHUSDT"),
        ("okx", _okx("BTC-USDT-SWAP"), "BTC-USDT-SWAP"),
    ],
)
def test_a_frame_names_its_symbol_in_the_configured_spelling(
    venue: str, frame: str, symbol: str
) -> None:
    assert rk.symbol_of(venue, frame) == symbol


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("venue", "frame"),
    [
        ("bybit", json.dumps({"success": True, "ret_msg": "", "conn_id": "x", "op": "subscribe"})),
        ("bybit", json.dumps({"success": True, "ret_msg": "pong", "op": "ping"})),
        ("okx", json.dumps({"event": "error", "msg": "Subscribe failed", "code": "60018"})),
        ("okx", "pong"),
        ("binance", json.dumps({"result": None, "id": 1})),
        ("binance", "not json at all"),
    ],
)
def test_a_pong_an_acknowledgement_or_an_error_names_no_symbol(venue: str, frame: str) -> None:
    assert rk.symbol_of(venue, frame) is None


# --- moving -------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_layout_a_moves_to_the_symbol_directory_and_the_source_goes() -> None:
    s3 = FakeS3()
    body = _seed(s3, _layout_a("binance", "1200"), [_binance("ETHUSDT")] * 3)

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.keys(B) == [_new("binance", "ETHUSDT", "1200")]
    assert s3.objects[(B, _new("binance", "ETHUSDT", "1200"))] == body
    assert report.moved == {("binance", "ETHUSDT"): 1}
    assert report.refused == []


@pytest.mark.trace("REQ-WP-078")
def test_layout_b_moves_and_the_venue_appears_once() -> None:
    s3 = FakeS3()
    _seed(s3, _layout_b("bybit", "1059", "2026/10/02"), [_bybit("BTCUSDT")] * 2)

    rk.rekey(s3, B, venues=("bybit",), apply=True)

    assert s3.keys(B) == [_new("bybit", "BTCUSDT", "1059", "2026/10/02")]


@pytest.mark.trace("REQ-WP-078")
def test_an_object_naming_two_symbols_is_refused_and_left_where_it_is() -> None:
    s3 = FakeS3()
    key = _layout_a("binance", "1200")
    body = _seed(s3, key, [_binance("ETHUSDT"), _binance("SOLUSDT")])

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.objects == {(B, key): body}
    assert [(k, r.split(":")[0]) for k, r in report.refused] == [(key, "several symbols")]
    assert "ETHUSDT" in report.refused[0][1] and "SOLUSDT" in report.refused[0][1]


@pytest.mark.trace("REQ-WP-078")
def test_an_object_of_only_acknowledgements_is_refused_not_guessed_at() -> None:
    s3 = FakeS3()
    key = _layout_b("bybit", "0001")
    _seed(s3, key, [json.dumps({"success": True, "op": "subscribe"})])

    report = rk.rekey(s3, B, venues=("bybit",), apply=True)

    assert s3.keys(B) == [key]
    assert report.refused == [(key, "no attributable frame")]


@pytest.mark.trace("REQ-WP-078")
def test_a_key_under_the_prefix_that_is_no_layout_is_refused() -> None:
    s3 = _store(**{"raw__cex__binance__notes.txt": b"hello"})

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.keys(B) == ["raw/cex/binance/notes.txt"]
    assert report.refused == [("raw/cex/binance/notes.txt", "key matches no known layout")]


# --- safety -------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_a_destination_that_already_holds_the_same_bytes_lets_the_source_go() -> None:
    s3 = FakeS3()
    src = _layout_a("binance", "1200")
    body = _seed(s3, src, [_binance("BTCUSDT")])
    s3.put_object(Bucket=B, Key=_new("binance", "BTCUSDT", "1200"), Body=body)

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.keys(B) == [_new("binance", "BTCUSDT", "1200")]
    assert report.already_there == 1 and report.refused == []


@pytest.mark.trace("REQ-WP-078")
def test_a_destination_holding_different_bytes_is_never_overwritten() -> None:
    s3 = FakeS3()
    src = _layout_a("binance", "1200")
    dst = _new("binance", "BTCUSDT", "1200")
    mine = _seed(s3, src, [_binance("BTCUSDT")])
    other = _body([_binance("BTCUSDT"), _binance("BTCUSDT")])
    s3.put_object(Bucket=B, Key=dst, Body=other)

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.objects == {(B, src): mine, (B, dst): other}
    assert report.refused == [(src, "destination holds different bytes")]


@pytest.mark.trace("REQ-WP-078")
def test_a_copy_that_does_not_verify_leaves_the_source_and_removes_the_bad_copy() -> None:
    s3 = FakeS3(corrupt_copies=True)
    src = _layout_a("binance", "1200")
    body = _seed(s3, src, [_binance("BTCUSDT")])

    report = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert s3.objects == {(B, src): body}, "the source must survive, and the bad copy must go"
    assert report.refused == [(src, "copy did not verify")]


@pytest.mark.trace("REQ-WP-078")
def test_an_interrupted_delete_loses_nothing_and_a_second_run_finishes() -> None:
    s3 = FakeS3()
    src = _layout_a("binance", "1200")
    dst = _new("binance", "BTCUSDT", "1200")
    body = _seed(s3, src, [_binance("BTCUSDT")])

    s3.fail_deletes = True
    first = rk.rekey(s3, B, venues=("binance",), apply=True)
    assert s3.objects == {(B, src): body, (B, dst): body}, "the worst state is a duplicate"
    assert len(first.refused) == 1 and "RuntimeError" in first.refused[0][1]

    s3.fail_deletes = False
    second = rk.rekey(s3, B, venues=("binance",), apply=True)
    assert s3.keys(B) == [dst]
    assert second.already_there == 1


@pytest.mark.trace("REQ-WP-078")
def test_a_dry_run_changes_nothing_and_says_what_it_would_do() -> None:
    s3 = FakeS3()
    _seed(s3, _layout_a("binance", "1200"), [_binance("ETHUSDT")])
    _seed(s3, _layout_b("bybit", "1200"), [_bybit("BTCUSDT")])
    before = s3.snapshot()
    s3.calls.clear()

    report = rk.rekey(s3, B, venues=("binance", "bybit"), apply=False)

    assert s3.snapshot() == before
    assert {op for op, _ in s3.calls} <= {"list", "get", "head"}, s3.calls
    assert report.applied is False
    assert report.moved == {("binance", "ETHUSDT"): 1, ("bybit", "BTCUSDT"): 1}


@pytest.mark.trace("REQ-WP-078")
def test_a_second_run_over_a_finished_migration_has_nothing_to_do() -> None:
    s3 = FakeS3()
    _seed(s3, _layout_a("binance", "1200"), [_binance("ETHUSDT")])
    rk.rekey(s3, B, venues=("binance",), apply=True)
    s3.calls.clear()

    again = rk.rekey(s3, B, venues=("binance",), apply=True)

    assert again.moved == {} and again.already_there == 0 and again.refused == []
    assert {op for op, _ in s3.calls} <= {"list"}, "nothing to read, copy or delete"


# --- the extent ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_the_report_states_the_overwrite_as_a_number_per_symbol() -> None:
    """Three symbols took turns winning each minute, so each is missing two minutes in three."""
    s3 = FakeS3()
    order = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    for minute in range(9):
        _seed(s3, _layout_a("binance", f"12{minute:02d}"), [_binance(order[minute % 3])] * 2)

    report = rk.rekey(s3, B, venues=("binance",), apply=False)

    for symbol in order:
        assert report.minutes_present[("binance", symbol)] == 3
        assert report.minutes_expected[("binance", symbol)] == 9
        assert report.held_by_others("binance", symbol) == 6
    assert report.empty("binance") == 0
    rendered = report.render().lower()
    assert "the most that" in rendered and "cannot say" in rendered


@pytest.mark.trace("REQ-WP-078")
def test_a_stretch_with_no_object_is_empty_and_not_counted_as_overwritten() -> None:
    """Minutes in which no process ran are not minutes in which anything was overwritten.

    ETH's report once read 17,526 "missing" minutes, six days of which were a crash loop.
    Here BTC holds minutes 0-1 and 6-7; minutes 2-5 have no object at all.
    """
    s3 = FakeS3()
    for minute in (0, 1, 6, 7):
        _seed(s3, _layout_a("binance", f"12{minute:02d}"), [_binance("BTCUSDT")])

    report = rk.rekey(s3, B, venues=("binance",), apply=False)

    assert report.minutes_expected[("binance", "BTCUSDT")] == 8
    assert report.minutes_present[("binance", "BTCUSDT")] == 4
    assert report.empty("binance") == 4
    assert report.held_by_others("binance", "BTCUSDT") == 0


# --- the command --------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_the_command_is_a_dry_run_unless_told_otherwise(capsys: pytest.CaptureFixture[str]) -> None:
    s3 = FakeS3()
    _seed(s3, _layout_a("binance", "1200"), [_binance("BTCUSDT")])
    before = s3.snapshot()

    assert rk.main([], client=s3, bucket=B) == 0
    assert s3.snapshot() == before
    assert "dry-run" in capsys.readouterr().out.lower()

    assert rk.main(["--apply"], client=s3, bucket=B) == 0
    assert s3.keys(B) == [_new("binance", "BTCUSDT", "1200")]
