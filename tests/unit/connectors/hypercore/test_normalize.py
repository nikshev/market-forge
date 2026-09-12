"""HyperCore normalizes into the shared CLOB primitives (REQ-WP-048).

The fixture is one capture of the venue's public responses plus an interleaved
websocket recording of trades and quotes on a single connection. The interleaving
is what settles what `side` means, and the metadata is what makes the symbol
assertions possible: a docstring claiming delisted perps keep their index proves
nothing, and a test over 234 real assets does.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.connectors.hypercore.normalize import (
    CrossedBook,
    Namespace,
    NormalizationError,
    SymbolTable,
    UnknownSymbol,
    asset_context,
    best_bid_offer,
    evm_wei,
    order_book,
    public_trade,
)

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "hypercore" / "info.jsonl"


def _rows() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.hypercore_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


ROWS = _rows()
META = next(row for row in ROWS if row["kind"] == "meta")["body"]
SPOT_META = next(row for row in ROWS if row["kind"] == "spotMeta")["body"]
ALL_MIDS = next(row for row in ROWS if row["kind"] == "allMids")["body"]
CONTEXTS = next(row for row in ROWS if row["kind"] == "metaAndAssetCtxs")["body"]
PERP_DEXES = next(row for row in ROWS if row["kind"] == "perpDexs")["body"]
BOOKS = [row for row in ROWS if row["kind"] == "l2Book"]
STREAM = [row for row in ROWS if row["kind"] == "stream"]


@pytest.fixture
def table() -> SymbolTable:
    return SymbolTable(meta=META, spot_meta=SPOT_META, perp_dexes=PERP_DEXES)


def _trades() -> list[dict[str, Any]]:
    return [
        trade
        for row in STREAM
        if row["message"]["channel"] == "trades"
        for trade in row["message"]["data"]
    ]


# --- the index conventions, which fail in opposite directions -----------------


@pytest.mark.trace("REQ-WP-048")
def test_a_delisted_perp_keeps_its_index(table: SymbolTable) -> None:
    """`metaAndAssetCtxs` is positional against the same list, so an index that
    skipped delisted assets would pair one asset's context with another's name --
    two live markets' numbers under one symbol."""
    universe = META["universe"]
    delisted = sorted(index for index, asset in enumerate(universe) if asset.get("isDelisted"))
    assert delisted, "no delisted perp in the capture; the assertion cannot bite"
    for index in delisted:
        assert table.perp_at(index) == universe[index]["name"]

    # And the compacted table really does disagree, from the first gap onward.
    listed_only = [asset["name"] for asset in universe if not asset.get("isDelisted")]
    first_gap = delisted[0]
    assert listed_only[first_gap] != table.perp_at(first_gap)
    # Everything before the first gap agrees, which is why the error is quiet.
    for index in range(first_gap):
        assert listed_only[index] == table.perp_at(index)


@pytest.mark.trace("REQ-WP-048")
def test_a_spot_pair_is_found_by_its_index_and_not_its_position(table: SymbolTable) -> None:
    """The opposite mistake to the one above, on the same venue."""
    pairs = SPOT_META["universe"]
    indices = [pair["index"] for pair in pairs]
    assert max(indices) > len(pairs), "the capture's spot indices are dense; recapture"
    for pair in pairs:
        assert table.spot_at(pair["index"]) == pair["name"]

    by_position = [pair["name"] for pair in pairs]
    disagreements = [
        pair["index"]
        for position, pair in enumerate(pairs)
        if pair["index"] < len(by_position) and by_position[pair["index"]] != pair["name"]
    ]
    assert disagreements, (
        "every pair's index matched some position's name, so reading by position "
        "would have worked and this test proves nothing"
    )
    # And the disagreement is a real name collision, not an absence: reading by
    # position returns a different *live pair's* name for that index.
    index = disagreements[0]
    assert by_position[index] != table.spot_at(index)
    assert by_position[index] in {pair["name"] for pair in pairs}


@pytest.mark.trace("REQ-WP-048")
def test_a_perp_index_outside_the_venue_is_refused(table: SymbolTable) -> None:
    with pytest.raises(UnknownSymbol):
        table.perp_at(table.perp_count)
    with pytest.raises(UnknownSymbol):
        table.perp_at(-1)


# --- the three key shapes ------------------------------------------------------


@pytest.mark.trace("REQ-WP-048")
def test_the_capture_really_does_carry_three_key_shapes() -> None:
    """Otherwise everything below is about a venue that does not exist."""
    shapes = {"bare": 0, "@": 0, "#": 0}
    for key in ALL_MIDS:
        shapes["@" if key.startswith("@") else "#" if key.startswith("#") else "bare"] += 1
    assert all(count > 0 for count in shapes.values()), shapes


@pytest.mark.trace("REQ-WP-048")
def test_a_bare_key_resolves_to_a_perp(table: SymbolTable) -> None:
    namespace, name = table.resolve("BTC")
    assert namespace is Namespace.PERP
    assert name == "BTC"


@pytest.mark.trace("REQ-WP-048")
def test_an_at_key_resolves_to_a_spot_pair(table: SymbolTable) -> None:
    namespace, name = table.resolve("@0")
    assert namespace is Namespace.SPOT
    assert name == SPOT_META["universe"][0]["name"]


@pytest.mark.trace("REQ-WP-048")
def test_a_hash_key_is_refused_because_nobody_can_say_what_it_is(table: SymbolTable) -> None:
    """The honest answer, and the refusal says so rather than hiding it.

    Its values arrive in pairs summing to one, which is consistent with binary
    markets and is not evidence -- and a guess here would attribute a real series
    to an instrument nobody has identified.
    """
    hashed = next(key for key in ALL_MIDS if key.startswith("#"))
    with pytest.raises(UnknownSymbol, match="not established"):
        table.resolve(hashed)


@pytest.mark.trace("REQ-WP-048")
def test_the_hash_values_come_in_pairs_summing_to_one() -> None:
    """Recorded as the observation it is, so the refusal above has something
    concrete behind it and the next person can take it further."""
    hashed = sorted(key for key in ALL_MIDS if key.startswith("#"))
    pairs = 0
    for key in hashed:
        sibling = f"#{int(key[1:]) + 1}"
        if sibling in ALL_MIDS and int(key[1:]) % 10 == 0:
            total = Decimal(ALL_MIDS[key]) + Decimal(ALL_MIDS[sibling])
            assert abs(total - 1) < Decimal("0.01"), (key, sibling, total)
            pairs += 1
    assert pairs > 10, f"only {pairs} adjacent pairs found; the observation is thin"


@pytest.mark.trace("REQ-WP-048")
def test_a_builder_dex_asset_resolves_only_for_a_deployed_dex(table: SymbolTable) -> None:
    deployed = next(entry["name"] for entry in PERP_DEXES if entry)
    namespace, name = table.resolve(f"{deployed}:AAPL")
    assert namespace is Namespace.BUILDER_PERP
    assert name == f"{deployed}:AAPL"
    with pytest.raises(UnknownSymbol, match="no deployed perp dex"):
        table.resolve("nosuchdex:AAPL")
    with pytest.raises(UnknownSymbol, match="no asset"):
        table.resolve(f"{deployed}:")


@pytest.mark.trace("REQ-WP-048")
def test_the_two_endpoints_are_not_a_snapshot_of_each_other(table: SymbolTable) -> None:
    """Read seconds apart, and some keys in one match nothing in the other.

    Such a key is refused. Resolving it to a neighbour would attribute a live mid
    to the wrong pair, which is a plausible number and no symptom.
    """
    unresolved = []
    for key in ALL_MIDS:
        if not key.startswith("@"):
            continue
        try:
            table.resolve(key)
        except UnknownSymbol:
            unresolved.append(key)
    assert unresolved, "every '@' key resolved; the drift this guards against did not occur"
    for key in unresolved[:5]:
        with pytest.raises(UnknownSymbol, match="not in this metadata read"):
            table.resolve(key)


@pytest.mark.trace("REQ-WP-048")
@pytest.mark.parametrize("key", ["", "@", "@x", "@-1", "NOTACOIN", "btc", "BTC-USDT"])
def test_a_malformed_or_unknown_key_is_refused(table: SymbolTable, key: str) -> None:
    """Including a bare name that is not a perp, and a real perp in the wrong
    case: this venue's names are exact, and a near miss is still a miss."""
    with pytest.raises(UnknownSymbol):
        table.resolve(key)


# --- the book -----------------------------------------------------------------


@pytest.mark.trace("REQ-WP-048")
@pytest.mark.parametrize("row", BOOKS, ids=[row["coin"] for row in BOOKS])
def test_a_book_normalizes_with_its_sides_the_right_way_round(row: dict[str, Any]) -> None:
    snapshot = order_book(row["body"], market_type="perp", ingest_time_ns=7)
    assert snapshot.meta.symbol == row["coin"]
    assert snapshot.bids and snapshot.asks
    assert snapshot.bids[0].price < snapshot.asks[0].price
    # Bids descend from the best, asks ascend.
    assert [level.price for level in snapshot.bids] == sorted(
        (level.price for level in snapshot.bids), reverse=True
    )
    assert [level.price for level in snapshot.asks] == sorted(
        level.price for level in snapshot.asks
    )
    assert snapshot.meta.ingest_time_ns == 7
    assert snapshot.meta.event_time_ns == row["body"]["time"] * 1_000_000


@pytest.mark.trace("REQ-WP-048")
def test_reading_the_sides_in_the_wrong_order_is_refused_not_published() -> None:
    """`levels` is positional, so the wrong order gives a *crossed* book -- and a
    crossed book is a tradeable signal, which makes that error worse than a
    missing one."""
    body = dict(BOOKS[0]["body"])
    bids, asks = body["levels"]
    body["levels"] = [asks, bids]
    with pytest.raises(CrossedBook):
        order_book(body, market_type="perp", ingest_time_ns=7)


@pytest.mark.trace("REQ-WP-048")
def test_a_book_with_the_wrong_number_of_sides_is_refused() -> None:
    body = dict(BOOKS[0]["body"])
    body["levels"] = [body["levels"][0]]
    with pytest.raises(NormalizationError, match="two sides"):
        order_book(body, market_type="perp", ingest_time_ns=7)


@pytest.mark.trace("REQ-WP-048")
def test_the_quote_stream_normalizes_as_a_two_level_book() -> None:
    quotes = [row for row in STREAM if row["message"]["channel"] == "bbo"]
    assert quotes, "the capture recorded no quotes"
    for row in quotes[:20]:
        snapshot = best_bid_offer(row["message"]["data"], market_type="perp", ingest_time_ns=7)
        assert len(snapshot.bids) <= 1
        assert len(snapshot.asks) <= 1
        if snapshot.bids and snapshot.asks:
            assert snapshot.bids[0].price < snapshot.asks[0].price


@pytest.mark.trace("REQ-WP-048")
def test_an_empty_quote_side_is_absent_and_not_a_quote_of_zero() -> None:
    empty = best_bid_offer(
        {"coin": "BTC", "time": 1, "bbo": [None, {"px": "10", "sz": "1", "n": 1}]},
        market_type="perp",
        ingest_time_ns=7,
    )
    assert empty.bids == ()
    assert empty.asks[0].price == Decimal("10")


# --- trades -------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-048")
def test_the_side_field_is_the_taker_s_and_the_recording_says_so() -> None:
    """Measured, not assumed. `B` at or above the ask, `A` at or below the bid.

    A test rather than a docstring, because a test fails when the venue changes.
    """
    tally: dict[tuple[str, str], int] = {}
    for coin in {row["coin"] for row in STREAM}:
        bid = ask = None
        for row in (entry for entry in STREAM if entry["coin"] == coin):
            message = row["message"]
            if message["channel"] == "bbo":
                sides = message["data"]["bbo"]
                bid = Decimal(sides[0]["px"]) if sides[0] else bid
                ask = Decimal(sides[1]["px"]) if sides[1] else ask
                continue
            for trade in message["data"]:
                if bid is None or ask is None:
                    continue
                price = Decimal(trade["px"])
                where = (
                    "at_or_above_ask"
                    if price >= ask
                    else "at_or_below_bid"
                    if price <= bid
                    else "inside"
                )
                tally[trade["side"], where] = tally.get((trade["side"], where), 0) + 1

    lifted = tally.get(("B", "at_or_above_ask"), 0)
    hit = tally.get(("A", "at_or_below_bid"), 0)
    assert lifted > 20 and hit > 20, f"too few classifiable trades: {tally}"
    # Overwhelming, not unanimous: a trade can arrive before the quote update
    # that had already moved the price, which is what interleaving looks like.
    assert lifted / sum(count for (side, _), count in tally.items() if side == "B") > 0.9
    assert hit / sum(count for (side, _), count in tally.items() if side == "A") > 0.9
    assert not tally.get(("B", "at_or_below_bid"))
    assert not tally.get(("A", "at_or_above_ask"))


@pytest.mark.trace("REQ-WP-048")
def test_a_trade_normalizes_into_the_shared_trade_event() -> None:
    trade = _trades()[0]
    event = public_trade(trade, market_type="perp", ingest_time_ns=7)
    assert event.meta.venue == "hyperliquid"
    assert event.trade_id == str(trade["tid"])
    assert event.price == Decimal(trade["px"])
    # No contract multiplier on this venue, unlike OKX: size is already base.
    assert event.qty_base == Decimal(trade["sz"])
    assert event.notional_quote == event.price * event.qty_base
    assert event.aggressor_side == ("buy" if trade["side"] == "B" else "sell")
    assert event.is_buyer_maker == (trade["side"] == "A")
    # The venue stamps milliseconds and the domain holds nanoseconds. Left
    # unconverted the figure is still a plausible timestamp -- in 1970.
    assert event.meta.event_time_ns == trade["time"] * 1_000_000
    assert event.meta.ingest_time_ns == 7
    assert event.meta.sequence == int(trade["tid"])


@pytest.mark.trace("REQ-WP-048")
def test_trade_ids_are_unique_and_usable_for_de_duplication() -> None:
    """§18.25 asks for trade de-duplication, which needs a key that is actually
    a key. Asserted over the recording rather than assumed from the field name."""
    ids = [trade["tid"] for trade in _trades()]
    assert len(ids) > 100, f"only {len(ids)} trades recorded"
    assert len(set(ids)) == len(ids)


@pytest.mark.trace("REQ-WP-048")
def test_an_unknown_side_is_refused() -> None:
    trade = dict(_trades()[0]) | {"side": "X"}
    with pytest.raises(NormalizationError, match="unknown taker side"):
        public_trade(trade, market_type="perp", ingest_time_ns=7)


@pytest.mark.trace("REQ-WP-048")
@pytest.mark.parametrize("missing", ["side", "px", "sz", "tid", "time", "coin"])
def test_a_trade_missing_a_required_field_is_refused(missing: str) -> None:
    trade = {key: value for key, value in _trades()[0].items() if key != missing}
    with pytest.raises(NormalizationError):
        public_trade(trade, market_type="perp", ingest_time_ns=7)


# --- derivatives state ---------------------------------------------------------


@pytest.mark.trace("REQ-WP-048")
def test_an_asset_context_carries_funding_open_interest_and_a_reference_price() -> None:
    """§18.11.1's `derivatives.funding`, `derivatives.open_interest` and
    `market.reference_price`, from one payload."""
    context = CONTEXTS[1][0]
    state = asset_context(
        context, symbol="BTC", market_type="perp", event_time_ns=11, ingest_time_ns=13
    )
    assert state.funding_rate == float(context["funding"])
    assert state.open_interest_base == float(context["openInterest"])
    assert state.mark_price == Decimal(context["markPx"])
    assert state.index_price == Decimal(context["oraclePx"])
    assert state.basis_bps is not None
    assert state.meta.event_time_ns == 11


@pytest.mark.trace("REQ-WP-048")
def test_the_basis_is_the_mark_against_the_oracle_and_is_signed() -> None:
    """Signed by nature: a mark below its oracle is a real and common state."""
    below = asset_context(
        {"markPx": "99", "oraclePx": "100"},
        symbol="BTC",
        market_type="perp",
        event_time_ns=1,
        ingest_time_ns=2,
    )
    above = asset_context(
        {"markPx": "101", "oraclePx": "100"},
        symbol="BTC",
        market_type="perp",
        event_time_ns=1,
        ingest_time_ns=2,
    )
    assert below.basis_bps == pytest.approx(-100.0)
    assert above.basis_bps == pytest.approx(100.0)


@pytest.mark.trace("REQ-WP-048")
def test_an_absent_field_stays_absent_rather_than_becoming_zero() -> None:
    """A funding rate of zero is a market in balance; one nobody published is a
    market nobody measured, and flattening the second into the first is the error
    [[REQ-WP-031]] is named after."""
    silent = asset_context({}, symbol="BTC", market_type="perp", event_time_ns=1, ingest_time_ns=2)
    assert silent.funding_rate is None
    assert silent.open_interest_base is None
    assert silent.mark_price is None
    assert silent.index_price is None
    assert silent.basis_bps is None

    balanced = asset_context(
        {"funding": "0.0", "openInterest": "0.0"},
        symbol="BTC",
        market_type="perp",
        event_time_ns=1,
        ingest_time_ns=2,
    )
    assert balanced.funding_rate == 0.0
    assert balanced.open_interest_base == 0.0


@pytest.mark.trace("REQ-WP-048")
def test_every_asset_context_lines_up_with_the_uncompacted_universe(table: SymbolTable) -> None:
    """The contexts are positional against `meta.universe`, delisted included, so
    this is the index convention above with real consequences attached."""
    contexts = CONTEXTS[1]
    assert len(contexts) == table.perp_count
    for index, context in enumerate(contexts):
        state = asset_context(
            context,
            symbol=table.perp_at(index),
            market_type="perp",
            event_time_ns=1,
            ingest_time_ns=2,
        )
        assert state.meta.symbol == META["universe"][index]["name"]


# --- the cross-layer units hazard ---------------------------------------------


@pytest.mark.trace("REQ-WP-048")
def test_a_token_s_evm_amount_needs_its_extra_decimals(table: SymbolTable) -> None:
    """§18.11.3 compares a HyperCore mid against a HyperEVM DEX price. USDC is
    eight wei decimals on HyperCore and `-2` extra on EVM, so ignoring the offset
    is a factor of a hundred -- which would read as an arbitrage."""
    _, quote = table.pair_tokens(0)
    extra = quote["evmContract"]["evm_extra_wei_decimals"]
    assert extra != 0, "the capture's quote token has no offset; pick another pair"
    naive = int(Decimal("1.5") * Decimal(10) ** quote["weiDecimals"])
    assert evm_wei(quote, Decimal("1.5")) != naive
    assert evm_wei(quote, Decimal("1.5")) == int(
        Decimal("1.5") * Decimal(10) ** (quote["weiDecimals"] + extra)
    )


@pytest.mark.trace("REQ-WP-048")
def test_a_token_with_no_evm_contract_is_refused(table: SymbolTable) -> None:
    with pytest.raises(UnknownSymbol, match="no HyperEVM contract"):
        evm_wei({"name": "NOEVM", "weiDecimals": 8}, Decimal("1"))


@pytest.mark.trace("REQ-WP-048")
def test_an_offset_below_zero_decimals_is_refused() -> None:
    with pytest.raises(NormalizationError, match="decimals"):
        evm_wei(
            {"name": "ODD", "weiDecimals": 1, "evmContract": {"evm_extra_wei_decimals": -5}},
            Decimal("1"),
        )


# --- provenance ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-048")
def test_the_capture_was_one_pass() -> None:
    """The metadata and the mids have to be close together for the staleness
    measured above to be the venue's rather than the tool's."""
    capture = next(row for row in ROWS if row["kind"] == "capture")
    assert capture["elapsed_ns"] < 300 * 1_000_000_000
    assert capture["endpoint"].startswith("https://")


@pytest.mark.trace("REQ-WP-048")
def test_trades_and_quotes_share_a_recording() -> None:
    """Separated, they cannot answer what `side` means."""
    channels = {row["message"]["channel"] for row in STREAM}
    assert channels == {"trades", "bbo"}
    ordered = [row["received_ns"] for row in STREAM]
    assert ordered == sorted(ordered)
