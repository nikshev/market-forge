"""`CUSTOM_ACCOUNTING` pools are quoted, never curved (REQ-WP-071).

The fixture is what Ethereum mainnet answered at block 25975796: four pools, a
four-rung size ladder each, and every refusal recorded verbatim. Amounts are
asserted as exact integers, because the failure this requirement exists to catch
produces a number that is positive, ordered and believable -- an assertion of
`> 0` would pass for all of them.
"""

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.chain.providers import CallReverted
from channelflow.dex.depth import depth_to_bps
from channelflow.dex.pool import PoolState
from channelflow.dex.reconstruction import require_tick_map_complete
from channelflow.dex.uniswap_v4 import (
    CURVE_RECONSTRUCTIBLE,
    CurveDoesNotApply,
    PoolKey,
    PoolRegistry,
    ReconstructionClass,
    RoutingKey,
    classify,
    require_curve_applies,
)
from channelflow.dex.v4_quoting import (
    POOL_MANAGER_SELECTOR,
    UNEXPECTED_REVERT_BYTES,
    ExecutableQuoter,
    NoTwoSidedMarket,
    Quote,
    QuoteRefused,
    QuoteRequest,
    QuoteUnavailable,
    RefusalReason,
    WrongQuoter,
    decode_refusal,
    encode_exact_input_single,
    implied_price,
    selector,
)
from tests.unit.dex.replay_provider import QuoteNotCaptured, ReplayProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "uniswap_v4"
QUOTES = FIXTURES / "quotes.jsonl"
INITIALIZE = FIXTURES / "initialize.jsonl"

CHAIN_ID = 1
BLOCK = 25975796

#: The pools, by the shorthand the notes use for them.
DEEP = "0xf7caa8ee16fff4e0cd360f9248c1dde011a28a0de3038845c85b904cda1c9b75"
PINNED = "0x5d10cbe0fdcd8b52e0cf64e84d692b124396a1be49d2b77c1665293bcd855ab4"
EMPTY = "0x5ce617f9e436c9e71c6de6306bc5a466fe2ef4145649d6b5ef9aa8a27ed530c1"
TWO_SIDED = "0x88249e685c939f1f1100c5f394a956e13585a4baa485115095f82dd08929ff9e"

SIZES = (10**15, 10**16, 10**17, 10**18)


def _defined_names(source: str) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef | ast.FunctionDef)
    }


def _rows() -> list[dict[str, Any]]:
    assert QUOTES.is_file(), (
        f"missing fixture {QUOTES}; regenerate with tools.record.v4_quote_capture"
    )
    return [json.loads(line) for line in QUOTES.read_text().splitlines()]


@pytest.fixture
def rows() -> list[dict[str, Any]]:
    return _rows()


@pytest.fixture
def states(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["pool_id"]: row for row in rows if row["kind"] == "state"}


@pytest.fixture
def provider() -> ReplayProvider:
    return ReplayProvider(QUOTES)


@pytest.fixture
def registry(states: dict[str, dict[str, Any]], provider: ReplayProvider) -> PoolRegistry:
    built = PoolRegistry()
    for state in states.values():
        built.initialised(
            chain_id=CHAIN_ID,
            pool_manager=provider.pool_manager,
            key=PoolKey(
                state["currency0"],
                state["currency1"],
                state["fee"],
                state["tick_spacing"],
                state["hooks"],
            ),
        )
    return built


@pytest.fixture
def quoter(provider: ReplayProvider, registry: PoolRegistry) -> ExecutableQuoter:
    return ExecutableQuoter(
        provider,
        registry,
        address=provider.quoter,
        pool_manager=provider.pool_manager,
        block=provider.block,
    )


def _route(pool_id_hex: str, provider: ReplayProvider) -> RoutingKey:
    return RoutingKey(chain_id=CHAIN_ID, pool_manager=provider.pool_manager, pool_id=pool_id_hex)


def _pool_state(state: dict[str, Any]) -> PoolState:
    return PoolState(
        address=state["pool_id"],
        token0=state["currency0"],
        token1=state["currency1"],
        fee_tier=state["fee"],
        tick_spacing=state["tick_spacing"],
        current_tick=state["tick"],
        sqrt_price_x96=int(state["sqrt_price_x96"]),
        active_liquidity=Decimal(state["liquidity"]),
    )


# --- T001: the fixture is what we think it is -------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_fixture_holds_one_block_and_every_answer(rows: list[dict[str, Any]]) -> None:
    kinds = [row["kind"] for row in rows]
    assert kinds.count("quoter") == 1
    assert kinds.count("state") == 4
    forward = [r for r in rows if r["kind"] in {"quote", "refusal"} and r["zero_for_one"]]
    reverse = [r for r in rows if r["kind"] in {"quote", "refusal"} and not r["zero_for_one"]]
    assert len(forward) == 16, "four pools, four rungs each"
    assert len(reverse) == 3, "one reverse answer per pool whose 1e16 rung quoted"
    assert len(rows) == 24
    header = next(row for row in rows if row["kind"] == "quoter")
    assert header["block"] == BLOCK
    assert header["chain_id"] == CHAIN_ID
    assert header["pool_manager"] == "0x000000000004444c5dc75cb358380d2e3de08a90"


# --- T008: what the curve says when the gate is bypassed --------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_tick_path_calls_a_pool_that_absorbs_an_ether_unmovable(
    states: dict[str, dict[str, Any]], rows: list[dict[str, Any]]
) -> None:
    """The hazard, asserted rather than assumed away.

    `require_tick_map_complete` passes here and is right to: an empty tick map
    explains a pool reporting zero liquidity exactly. It answers a different
    question. The information that would catch this is the hook address, which
    is why the gate is on the class and this test goes round it on purpose.
    """
    state = _pool_state(states[DEEP])
    assert state.active_liquidity == 0

    require_tick_map_complete(state)  # passes -- 0 == 0

    verdict = depth_to_bps(state, bps=Decimal(50), upward=True)
    assert verdict.reachable is False
    assert verdict.amount0 == 0
    assert verdict.amount1 == 0
    assert verdict.reason == "the pool has no active liquidity, so its price cannot be moved"

    quoted = next(
        row
        for row in rows
        if row["kind"] == "quote"
        and row["pool_id"] == DEEP
        and row["zero_for_one"]
        and row["exact_amount"] == str(10**18)
    )
    assert quoted["amount_out"] == "496412035653451820217981817"


# --- T009/T010: the gate ----------------------------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_gate_refuses_every_custom_accounting_pool_in_the_fixture(
    states: dict[str, dict[str, Any]],
) -> None:
    assert len(states) == 4
    for pool, state in states.items():
        key = PoolKey(
            state["currency0"],
            state["currency1"],
            state["fee"],
            state["tick_spacing"],
            state["hooks"],
        )
        assert classify(key) is ReconstructionClass.CUSTOM_ACCOUNTING
        with pytest.raises(CurveDoesNotApply) as raised:
            require_curve_applies(key)
        assert pool[2:12] in str(raised.value)
        assert "CUSTOM_ACCOUNTING" in str(raised.value)


@pytest.mark.trace("REQ-WP-071")
def test_the_gate_passes_the_three_classes_that_permit_reconstruction() -> None:
    rows = [json.loads(line) for line in INITIALIZE.read_text().splitlines()]
    seen: set[ReconstructionClass] = set()
    for row in rows:
        if row.get("kind") != "pool":
            continue
        key = PoolKey(
            row["currency0"], row["currency1"], row["fee"], row["tick_spacing"], row["hooks"]
        )
        found = classify(key)
        if found is ReconstructionClass.CUSTOM_ACCOUNTING:
            continue
        seen.add(found)
        assert require_curve_applies(key) is None
    assert seen == {
        ReconstructionClass.STANDARD_CL,
        ReconstructionClass.DYNAMIC_FEE_CL,
        ReconstructionClass.HOOK_AUGMENTED_CL,
    }


@pytest.mark.trace("REQ-WP-071")
def test_unknown_is_excluded_alongside_custom_accounting() -> None:
    assert CURVE_RECONSTRUCTIBLE == frozenset(
        {
            ReconstructionClass.STANDARD_CL,
            ReconstructionClass.DYNAMIC_FEE_CL,
            ReconstructionClass.HOOK_AUGMENTED_CL,
        }
    )
    # A hook holding a returns-delta bit without the action bit is invalid, so
    # the manager would have rejected the key: `classify` says UNKNOWN.
    invalid = PoolKey(
        "0x0000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111",
        3000,
        60,
        "0x0000000000000000000000000000000000000008",
    )
    assert classify(invalid) is ReconstructionClass.UNKNOWN
    with pytest.raises(CurveDoesNotApply):
        require_curve_applies(invalid)


# --- T004/T005: the encoder -------------------------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_encoder_sign_extends_tick_spacing_across_a_whole_word(
    states: dict[str, dict[str, Any]],
) -> None:
    state = states[DEEP]
    key = PoolKey(
        state["currency0"], state["currency1"], state["fee"], state["tick_spacing"], state["hooks"]
    )
    data = encode_exact_input_single(key, zero_for_one=True, exact_amount=10**18)
    assert data[:10] == "0xaa9d21cb"
    words = [data[10 + i * 64 : 10 + (i + 1) * 64] for i in range(9)]
    assert int(words[0], 16) == 32, "the struct is dynamic; the head is an offset"
    assert int(words[1], 16) == int(state["currency0"], 16)
    assert int(words[2], 16) == int(state["currency1"], 16)
    assert int(words[3], 16) == 0
    assert int(words[4], 16) == 200
    assert int(words[5], 16) == int(state["hooks"], 16)
    assert int(words[6], 16) == 1
    assert int(words[7], 16) == 10**18
    assert int(words[8], 16) == 8 * 32, "offset to hookData, from the start of the tuple"
    assert int(data[10 + 9 * 64 :], 16) == 0, "hookData is empty"


@pytest.mark.trace("REQ-WP-071")
def test_a_negative_tick_spacing_fills_the_word() -> None:
    key = PoolKey(
        "0x0000000000000000000000000000000000000000",
        "0x1111111111111111111111111111111111111111",
        3000,
        -1,
        "0x0000000000000000000000000000000000000000",
    )
    data = encode_exact_input_single(key, zero_for_one=False, exact_amount=1)
    word = data[10 + 4 * 64 : 10 + 5 * 64]
    assert word == "f" * 64, "int24 -1 sign-extends to 256 bits, not 0x000000ffffff"


# --- T012-T016: quotes ------------------------------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_a_quote_request_refuses_a_size_that_is_not_a_size(provider: ReplayProvider) -> None:
    route = _route(DEEP, provider)
    for bad in (0, -1):
        with pytest.raises(ValueError, match="exact_amount"):
            QuoteRequest(route=route, zero_for_one=True, exact_amount=bad)


@pytest.mark.trace("REQ-WP-071")
def test_every_captured_quote_replays_to_its_exact_amount(
    quoter: ExecutableQuoter, provider: ReplayProvider, rows: list[dict[str, Any]]
) -> None:
    quoted = [row for row in rows if row["kind"] == "quote"]
    assert len(quoted) == 13, "12 forward rungs and one reverse"
    for row in quoted:
        request = QuoteRequest(
            route=_route(row["pool_id"], provider),
            zero_for_one=row["zero_for_one"],
            exact_amount=int(row["exact_amount"]),
        )
        answer = quoter.quote(request)
        assert answer.amount_out == int(row["amount_out"])
        assert answer.gas_estimate == row["gas_estimate"]
        assert answer.block == BLOCK
        assert answer.request == request


@pytest.mark.trace("REQ-WP-071")
def test_the_deep_pool_absorbs_an_ether(quoter: ExecutableQuoter, provider: ReplayProvider) -> None:
    answer = quoter.quote(
        QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=10**18)
    )
    assert answer.amount_out == 496412035653451820217981817
    assert answer.gas_estimate == 253482


@pytest.mark.trace("REQ-WP-071")
def test_a_quote_of_zero_cannot_be_built(provider: ReplayProvider) -> None:
    request = QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=1)
    with pytest.raises(ValueError, match="amount_out"):
        Quote(request=request, block=BLOCK, amount_out=0, gas_estimate=1)


@pytest.mark.trace("REQ-WP-071")
def test_the_two_directions_are_not_reciprocal_and_selling_is_the_worse_side(
    quoter: ExecutableQuoter, provider: ReplayProvider, rows: list[dict[str, Any]]
) -> None:
    """The gap between them is the round trip cost, not noise."""
    buy = quoter.quote(
        QuoteRequest(route=_route(TWO_SIDED, provider), zero_for_one=True, exact_amount=10**16)
    )
    reverse = next(
        row
        for row in rows
        if row["kind"] == "quote" and row["pool_id"] == TWO_SIDED and not row["zero_for_one"]
    )
    sell = quoter.quote(
        QuoteRequest(
            route=_route(TWO_SIDED, provider),
            zero_for_one=False,
            exact_amount=int(reverse["exact_amount"]),
        )
    )
    buy_price = implied_price(buy)
    sell_price = implied_price(sell)
    assert buy_price == Decimal("746527124.6970774645442279")
    assert sell_price > buy_price, "you pay more per unit to sell than you got to buy"
    gap = (sell_price - buy_price) / buy_price
    assert gap.quantize(Decimal("1e-12")) == Decimal("0.019346700318")


# --- T017-T023: refusals ----------------------------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_empty_pool_refuses_at_every_rung_and_names_itself(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    for size in SIZES:
        with pytest.raises(QuoteRefused) as raised:
            quoter.quote(
                QuoteRequest(route=_route(EMPTY, provider), zero_for_one=True, exact_amount=size)
            )
        assert raised.value.reason is RefusalReason.NOT_ENOUGH_LIQUIDITY
        assert raised.value.named_pool_id == EMPTY
        assert raised.value.request.exact_amount == size


@pytest.mark.trace("REQ-WP-071")
def test_the_pinned_pool_refuses_to_be_pushed_past_the_top_of_the_range(
    quoter: ExecutableQuoter,
    provider: ReplayProvider,
    rows: list[dict[str, Any]],
    states: dict[str, dict[str, Any]],
) -> None:
    reverse = next(
        row
        for row in rows
        if row["kind"] == "refusal" and row["pool_id"] == PINNED and not row["zero_for_one"]
    )
    with pytest.raises(QuoteRefused) as raised:
        quoter.quote(
            QuoteRequest(
                route=_route(PINNED, provider),
                zero_for_one=False,
                exact_amount=int(reverse["exact_amount"]),
            )
        )
    assert raised.value.reason is RefusalReason.PRICE_LIMIT_ALREADY_EXCEEDED
    assert raised.value.named_pool_id is None, "this error carries prices, not a pool id"
    assert raised.value.raw == reverse["revert_data"]
    assert raised.value.arguments == (
        1461446703485210103287273052203988822378723970341,
        1461446703485210103287273052203988822378723970341,
    )
    assert str(raised.value.arguments[0]) == states[PINNED]["sqrt_price_x96"]


@pytest.mark.trace("REQ-WP-071")
def test_the_deep_pool_sells_but_will_not_buy_back(
    quoter: ExecutableQuoter, provider: ReplayProvider, rows: list[dict[str, Any]]
) -> None:
    reverse = next(
        row
        for row in rows
        if row["kind"] == "refusal" and row["pool_id"] == DEEP and not row["zero_for_one"]
    )
    assert reverse["exact_amount"] == "9761282090570549416434980", (
        "the exact amount the pool had just offered for 0.01 ETH"
    )
    with pytest.raises(QuoteRefused) as raised:
        quoter.quote(
            QuoteRequest(
                route=_route(DEEP, provider),
                zero_for_one=False,
                exact_amount=int(reverse["exact_amount"]),
            )
        )
    assert raised.value.reason is RefusalReason.NOT_ENOUGH_LIQUIDITY
    assert raised.value.named_pool_id == DEEP


@pytest.mark.trace("REQ-WP-071")
def test_an_unrecognised_selector_is_unknown_and_never_a_recognised_one() -> None:
    payload = "0x6190b2b0" + f"{32:064x}" + f"{4:064x}" + "deadbeef".ljust(64, "0")
    reason, named, arguments = decode_refusal(payload)
    assert reason is RefusalReason.UNKNOWN
    assert reason is not RefusalReason.NOT_ENOUGH_LIQUIDITY
    assert named is None
    assert arguments == ()


@pytest.mark.trace("REQ-WP-071")
def test_a_payload_that_is_not_a_wrapper_and_a_missing_payload_are_both_unknown() -> None:
    assert decode_refusal("0x7a5ed734" + "11" * 32)[0] is RefusalReason.UNKNOWN
    assert decode_refusal(None)[0] is RefusalReason.UNKNOWN
    assert decode_refusal("0x")[0] is RefusalReason.UNKNOWN


@pytest.mark.trace("REQ-WP-071")
def test_a_reason_inside_the_wrong_wrapper_is_not_read() -> None:
    """A well-formed `NotEnoughLiquidity` in a payload that is not our wrapper.

    Without the wrapper check this decodes perfectly, and a refusal from some
    other contract's error type would be reported as this pool's liquidity.
    """
    inner = selector("NotEnoughLiquidity(bytes32)")[2:] + EMPTY[2:]
    payload = (
        selector("SomeOtherWrapper(bytes)")
        + f"{32:064x}"
        + f"{len(inner) // 2:064x}"
        + inner.ljust(64, "0")
    )
    assert decode_refusal(payload) == (RefusalReason.UNKNOWN, None, ())

    # The same bytes inside the real wrapper *are* read, so the test above is
    # about the wrapper and not about an unparseable payload.
    wrapped = (
        UNEXPECTED_REVERT_BYTES + f"{32:064x}" + f"{len(inner) // 2:064x}" + inner.ljust(64, "0")
    )
    reason, named, _ = decode_refusal(wrapped)
    assert reason is RefusalReason.NOT_ENOUGH_LIQUIDITY
    assert named == EMPTY


@pytest.mark.trace("REQ-WP-071")
@pytest.mark.parametrize("returned", ["0x", "0x" + f"{123:064x}"])
def test_a_return_too_short_to_hold_a_quote_is_not_decoded(
    registry: PoolRegistry, provider: ReplayProvider, returned: str
) -> None:
    """Half an answer is not an answer, and `int("", 16)` is not an amount."""

    class Truncating:
        name = "truncating"

        def get_block(self, number: int) -> dict[str, Any]:
            raise NotImplementedError

        def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]:
            raise NotImplementedError

        def eth_call(self, *, to: str, data: str, block: int) -> str:
            return returned

    truncating = ExecutableQuoter(
        Truncating(),
        registry,
        address=provider.quoter,
        pool_manager=provider.pool_manager,
        block=BLOCK,
    )
    with pytest.raises(QuoteUnavailable, match="bytes"):
        truncating.quote(
            QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=10**18)
        )


@pytest.mark.trace("REQ-WP-071")
def test_a_broken_endpoint_is_not_a_refusing_pool(
    registry: PoolRegistry, provider: ReplayProvider
) -> None:
    class Broken:
        name = "broken"

        def get_block(self, number: int) -> dict[str, Any]:
            raise NotImplementedError

        def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]:
            raise NotImplementedError

        def eth_call(self, *, to: str, data: str, block: int) -> str:
            raise TimeoutError("the node did not answer")

    broken = ExecutableQuoter(
        Broken(),
        registry,
        address=provider.quoter,
        pool_manager=provider.pool_manager,
        block=BLOCK,
    )
    with pytest.raises(QuoteUnavailable) as raised:
        broken.quote(
            QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=10**18)
        )
    assert not isinstance(raised.value, QuoteRefused)
    assert not issubclass(QuoteRefused, QuoteUnavailable)
    assert not issubclass(QuoteUnavailable, QuoteRefused)


@pytest.mark.trace("REQ-WP-071")
def test_a_refusal_is_asked_once_and_never_retried_smaller(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    before = len(provider.calls)
    with pytest.raises(QuoteRefused):
        quoter.quote(
            QuoteRequest(route=_route(EMPTY, provider), zero_for_one=True, exact_amount=10**18)
        )
    assert len(provider.calls) - before == 1


# --- T024-T027: the mid -----------------------------------------------------


@pytest.mark.trace("REQ-WP-071")
@pytest.mark.parametrize("pool", [DEEP, PINNED])
def test_a_one_sided_pool_has_no_mid(
    quoter: ExecutableQuoter, provider: ReplayProvider, pool: str
) -> None:
    with pytest.raises(NoTwoSidedMarket) as raised:
        quoter.mid(_route(pool, provider), size=10**16)
    assert isinstance(raised.value.__cause__, QuoteRefused)


@pytest.mark.trace("REQ-WP-071")
def test_the_two_sided_pool_has_a_mid_between_its_two_prices(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    mid = quoter.mid(_route(TWO_SIDED, provider), size=10**16)
    assert mid.quantize(Decimal("1e-10")) == Decimal("753713949.1600659021")
    assert Decimal("746527124.6970774645442279") < mid


@pytest.mark.trace("REQ-WP-071")
def test_a_mid_is_exactly_two_calls_at_one_block(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    before = len(provider.calls)
    quoter.mid(_route(TWO_SIDED, provider), size=10**16)
    made = provider.calls[before:]
    assert len(made) == 2
    assert {call[2] for call in made} == {BLOCK}


# --- T028-T030: the quoter names the manager --------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_a_verified_quoter_is_one_that_names_our_manager(quoter: ExecutableQuoter) -> None:
    assert quoter.verify() is None


@pytest.mark.trace("REQ-WP-071")
def test_a_quoter_naming_another_manager_is_refused_before_it_is_asked_anything(
    registry: PoolRegistry, provider: ReplayProvider
) -> None:
    impostor = ExecutableQuoter(
        provider,
        registry,
        address=provider.quoter,
        pool_manager="0x1111111111111111111111111111111111111111",
        block=BLOCK,
    )
    before = len(provider.calls)
    with pytest.raises(WrongQuoter) as raised:
        impostor.verify()
    assert provider.pool_manager in str(raised.value)
    assert "0x1111111111111111111111111111111111111111" in str(raised.value)
    made = provider.calls[before:]
    assert [call[1] for call in made] == [POOL_MANAGER_SELECTOR], "one call, and not a quote"


# --- T031-T033: replay is the same code -------------------------------------


@pytest.mark.trace("REQ-WP-071")
def test_the_adapter_knows_nothing_about_replay() -> None:
    """One code path. Replay substitutes the provider, never the adapter."""
    source = (
        Path(__file__).resolve().parents[3] / "src" / "channelflow" / "dex" / "v4_quoting.py"
    ).read_text()
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported, "parsed no imports at all; the check would pass vacuously"
    assert not any(name.startswith("tests") for name in imported)
    assert not any("replay" in name.lower() for name in imported)
    assert not any("Replay" in name for name in _defined_names(source))


@pytest.mark.trace("REQ-WP-071")
def test_a_question_the_chain_was_never_asked_is_not_answered_zero(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    with pytest.raises(QuoteNotCaptured):
        quoter.quote(
            QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=12345)
        )


@pytest.mark.trace("REQ-WP-071")
def test_every_call_names_the_adapters_own_block(
    quoter: ExecutableQuoter, provider: ReplayProvider
) -> None:
    quoter.verify()
    quoter.quote(QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=10**18))
    assert provider.calls, "the adapter made no calls at all"
    assert {call[2] for call in provider.calls} == {BLOCK}


@pytest.mark.trace("REQ-WP-071")
def test_a_revert_payload_the_endpoint_did_not_send_is_still_a_refusal(
    registry: PoolRegistry, provider: ReplayProvider
) -> None:
    class Silent:
        name = "silent"

        def get_block(self, number: int) -> dict[str, Any]:
            raise NotImplementedError

        def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]:
            raise NotImplementedError

        def eth_call(self, *, to: str, data: str, block: int) -> str:
            raise CallReverted("reverted, reason unstated", None)

    silent = ExecutableQuoter(
        Silent(),
        registry,
        address=provider.quoter,
        pool_manager=provider.pool_manager,
        block=BLOCK,
    )
    with pytest.raises(QuoteRefused) as raised:
        silent.quote(
            QuoteRequest(route=_route(DEEP, provider), zero_for_one=True, exact_amount=10**18)
        )
    assert raised.value.reason is RefusalReason.UNKNOWN
    assert raised.value.raw is None
