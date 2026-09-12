"""PRD section 18.11.2's HyperEVM pool events and cross-layer transfers (REQ-WP-058).

Every number asserted here was measured from chain 999 and is in
`tests/fixtures/hyperevm/`, recorded by `tools.record.hyperevm_capture` over
blocks 45722996-45723896. Nothing here reaches the network.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from channelflow.chain import ChainRecord, DecoderRegistry, ProtocolDecoder, RegistryEntry
from channelflow.chain.hyperevm import (
    FEE_TOPIC0,
    SWAP_TOPIC0,
    SYSTEM_BASE,
    TRANSFER_TOPIC0,
    CoreAmount,
    CoreAsset,
    FeeNotPublished,
    PoolFamily,
    RegisteredPool,
    Settlement,
    SwapDecoder,
    TokenFlow,
    TransferDirection,
    UnknownFactory,
    core_index_for,
    decode_cross_layer_transfer,
    decode_swap,
    family_for,
    pair_fees,
    settlement_of,
    settling_transfer,
    signed_word,
    to_core_amount,
    unsigned_word,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "hyperevm"

SECOND_NS = 1_000_000_000
BASE_NS = 1788838800000000000


def _rows(name: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (FIXTURES / name).read_text().splitlines()]


def _record(
    *,
    block: int,
    log_index: int,
    address: str,
    topics: list[str],
    data: str,
    transaction: str,
) -> ChainRecord:
    at = BASE_NS + block * SECOND_NS
    return ChainRecord(
        chain_id=999,
        network="hyperevm",
        block_number=block,
        block_hash=f"0xblock{block}",
        parent_hash=f"0xblock{block - 1}",
        block_time_ns=at,
        transaction_hash=transaction,
        transaction_index=0,
        log_index=log_index,
        address=address,
        topics=tuple(topics),
        data=data,
        observed_at_ns=at + SECOND_NS,
        available_at_ns=at + 2 * SECOND_NS,
        provider="rpc-a",
    )


def _swap_record(row: dict[str, Any]) -> ChainRecord:
    return _record(
        block=row["block"],
        log_index=row["log_index"],
        address=row["pool"],
        topics=row["topics"],
        data=row["data"],
        transaction=row["transaction"],
    )


def _transfer_records(row: dict[str, Any]) -> list[ChainRecord]:
    return [
        _record(
            block=row["block"],
            log_index=transfer["log_index"],
            address=transfer["token"],
            topics=transfer["topics"],
            data=transfer["data"],
            transaction=row["transaction"],
        )
        for transfer in row["transfers"]
    ]


@pytest.fixture(scope="module")
def swap_rows() -> list[dict[str, Any]]:
    return [row for row in _rows("swaps.jsonl") if row["kind"] == "swap"]


@pytest.fixture(scope="module")
def pool_rows() -> dict[str, dict[str, Any]]:
    return {row["address"]: row for row in _rows("swaps.jsonl") if row["kind"] == "pool"}


@pytest.fixture(scope="module")
def pools(pool_rows: dict[str, dict[str, Any]]) -> dict[str, RegisteredPool]:
    registered = {}
    for address, row in pool_rows.items():
        family = family_for(row["factory"])
        registered[address] = RegisteredPool(
            address=address,
            family=family,
            factory=row["factory"],
            token0=row["token0"],
            token1=row["token1"],
            tick_spacing=row["tick_spacing"],
            fee_pips=None if family in {PoolFamily.ALGEBRA_INTEGRAL} else row["fee_at_capture"],
        )
    return registered


@pytest.fixture(scope="module")
def assets() -> dict[int, CoreAsset]:
    return {
        row["index"]: CoreAsset(
            name=row["name"],
            index=row["index"],
            evm_contract=row["evm_contract"],
            evm_extra_wei_decimals=row["evm_extra_wei_decimals"],
            wei_decimals=row["wei_decimals"],
        )
        for row in _rows("cross_layer.jsonl")
        if row["kind"] == "core_asset"
    }


@pytest.fixture(scope="module")
def transfer_rows() -> list[dict[str, Any]]:
    return [row for row in _rows("cross_layer.jsonl") if row["kind"] == "system_transfer"]


# --------------------------------------------------------------------------
# The protocol is not in the event
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-058")
def test_both_families_emit_one_topic(
    swap_rows: list[dict[str, Any]], pool_rows: dict[str, dict[str, Any]]
) -> None:
    """The measurement the whole requirement rests on."""
    assert {row["family"] for row in pool_rows.values()} == {
        "uniswap_v3",
        "algebra_integral",
    }
    assert {row["topic0"] for row in swap_rows} == {SWAP_TOPIC0}
    payloads = {len(row["data"].removeprefix("0x")) for row in swap_rows}
    assert payloads == {5 * 64}, "both families carry the identical five-word payload"


@pytest.mark.trace("REQ-WP-058")
def test_family_comes_from_the_factory(pool_rows: dict[str, dict[str, Any]]) -> None:
    for row in pool_rows.values():
        assert family_for(row["factory"]) == row["family"]
    assert family_for("0xFF7B3E8C00E57EA31477C32A5B52A58EEA47B072") == PoolFamily.UNISWAP_V3


@pytest.mark.trace("REQ-WP-058")
def test_an_unmeasured_factory_is_refused() -> None:
    """130 addresses emit this topic on chain 999; two are measured."""
    with pytest.raises(UnknownFactory, match="not a measured"):
        family_for("0x" + "11" * 20)


@pytest.mark.trace("REQ-WP-058")
def test_a_dynamic_fee_pool_cannot_hold_a_pool_level_fee() -> None:
    with pytest.raises(ValueError, match="set per swap"):
        RegisteredPool(
            address="0xbe512f5881b85c48d9c17bc5bb2be047d156d696",
            family=PoolFamily.ALGEBRA_INTEGRAL,
            factory="0xf77bd082c627aa54591cf2f2eaa811fd1ab3b1f3",
            token0="0x5555555555555555555555555555555555555555",
            token1="0xb88339cb7199b77e23db6e890353e22632ba630f",
            tick_spacing=5,
            fee_pips=1069,
        )


@pytest.mark.trace("REQ-WP-058")
def test_an_immutable_fee_pool_must_record_its_fee() -> None:
    with pytest.raises(ValueError, match="immutable"):
        RegisteredPool(
            address="0x6c9a33e3b592c0d65b3ba59355d5be0d38259285",
            family=PoolFamily.UNISWAP_V3,
            factory="0xff7b3e8c00e57ea31477c32a5b52a58eea47b072",
            token0="0x5555555555555555555555555555555555555555",
            token1="0xb88339cb7199b77e23db6e890353e22632ba630f",
            tick_spacing=10,
        )


# --------------------------------------------------------------------------
# The fee
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-058")
def test_an_algebra_swap_alone_has_no_fee(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """Absent is not zero, and is not the pool's current fee."""
    row = next(row for row in swap_rows if pools[row["pool"]].dynamic_fee)
    swap = decode_swap(_swap_record(row), pools[row["pool"]])
    assert swap.fee_pips is None
    with pytest.raises(FeeNotPublished, match="per swap"):
        _ = swap.fee


@pytest.mark.trace("REQ-WP-058")
def test_a_uniswap_swap_carries_the_pools_immutable_fee(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    row = next(row for row in swap_rows if not pools[row["pool"]].dynamic_fee)
    swap = decode_swap(_swap_record(row), pools[row["pool"]])
    assert swap.fee == 500


@pytest.mark.trace("REQ-WP-058")
def test_every_algebra_swap_pairs_with_its_published_fee(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    paired = 0
    for row in swap_rows:
        if row["fee_pips"] is None:
            continue
        logs = [
            _swap_record(row),
            _record(
                block=row["block"],
                log_index=row["fee_log_index"],
                address=row["pool"],
                topics=[FEE_TOPIC0],
                data=f"0x{row['fee_pips']:064x}",
                transaction=row["transaction"],
            ),
        ]
        fees = pair_fees(logs)
        assert fees[row["log_index"]] == row["fee_pips"]
        paired += 1
    assert paired == 30, "every captured Algebra swap has a published fee"


@pytest.mark.trace("REQ-WP-058")
def test_the_fee_log_is_not_at_a_fixed_offset(swap_rows: list[dict[str, Any]]) -> None:
    """A pairing rule using a constant offset would pass on most of the sample."""
    distances = Counter(
        row["log_index"] - row["fee_log_index"] for row in swap_rows if row["fee_pips"] is not None
    )
    assert set(distances) == {3, 6, 7, 10}


@pytest.mark.trace("REQ-WP-058")
def test_the_pools_own_fee_misprices_most_of_its_swaps(
    swap_rows: list[dict[str, Any]], pool_rows: dict[str, dict[str, Any]]
) -> None:
    """The number a decoder gets by asking the pool instead of reading the log."""
    algebra = next(row for row in pool_rows.values() if row["family"] == "algebra_integral")
    published = [row["fee_pips"] for row in swap_rows if row["fee_pips"] is not None]
    assert sorted(set(published)) == [1069, 1070, 1071]
    assert algebra["fee_at_capture"] == 1069
    wrong = sum(1 for fee in published if fee != algebra["fee_at_capture"])
    assert (wrong, len(published)) == (26, 30)


@pytest.mark.trace("REQ-WP-058")
def test_two_swaps_in_one_transaction_take_their_own_fees(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """Each swap is priced by the fee published for it, not by the first one."""
    row = next(row for row in swap_rows if row["fee_pips"] is not None)
    pool = row["pool"]
    logs = [
        _record(
            block=1,
            log_index=0,
            address=pool,
            topics=[FEE_TOPIC0],
            data=f"0x{900:064x}",
            transaction="0xtx",
        ),
        _record(
            block=1,
            log_index=1,
            address=pool,
            topics=row["topics"],
            data=row["data"],
            transaction="0xtx",
        ),
        _record(
            block=1,
            log_index=2,
            address=pool,
            topics=[FEE_TOPIC0],
            data=f"0x{1100:064x}",
            transaction="0xtx",
        ),
        _record(
            block=1,
            log_index=9,
            address=pool,
            topics=row["topics"],
            data=row["data"],
            transaction="0xtx",
        ),
    ]
    assert pair_fees(logs) == {1: 900, 9: 1100}


@pytest.mark.trace("REQ-WP-058")
def test_a_swap_with_no_preceding_fee_log_is_left_unpriced(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    row = next(row for row in swap_rows if row["fee_pips"] is not None)
    assert pair_fees([_swap_record(row)]) == {}


# --------------------------------------------------------------------------
# The payload, and the oracle that checks it (ADR-067)
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-058")
def test_every_moving_side_agrees_with_the_transfer_that_settled_it(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    outcomes: Counter[Settlement] = Counter()
    for row in swap_rows:
        pool = pools[row["pool"]]
        swap = decode_swap(_swap_record(row), pool)
        transfers = _transfer_records(row)
        for token, amount in ((pool.token0, swap.amount0), (pool.token1, swap.amount1)):
            flow = settling_transfer(
                pool=pool.address,
                token=token,
                swap_log_index=row["log_index"],
                transfers=transfers,
            )
            outcome = settlement_of(amount, flow)
            assert outcome is not Settlement.MISMATCHED, (
                f"block {row['block']} log {row['log_index']} {token}"
            )
            outcomes[outcome] += 1
    assert outcomes[Settlement.MATCHED] == 164
    assert outcomes[Settlement.ZERO_SIDE] == 2


@pytest.mark.trace("REQ-WP-058")
def test_netting_the_whole_transaction_would_not_agree(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """Why the rule is "nearest preceding" and not "net the receipt"."""
    disagreements = 0
    for row in swap_rows:
        pool = pools[row["pool"]]
        swap = decode_swap(_swap_record(row), pool)
        net: Counter[str] = Counter()
        for transfer in row["transfers"]:
            if transfer["to"].lower() == pool.address:
                net[transfer["token"]] += int(transfer["amount"])
            if transfer["from"].lower() == pool.address:
                net[transfer["token"]] -= int(transfer["amount"])
        if net[pool.token0] != swap.amount0 or net[pool.token1] != swap.amount1:
            disagreements += 1
    assert disagreements > 0, "the coarse rule is wrong on real transactions"


@pytest.mark.trace("REQ-WP-058")
def test_the_tick_is_sign_extended_across_a_full_word(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """An unsigned read of the word gives a number, and it is not a tick."""
    ticks = []
    for row in swap_rows:
        swap = decode_swap(_swap_record(row), pools[row["pool"]])
        assert swap.tick == row["tick"]
        ticks.append(swap.tick)
    assert max(ticks) < 0, "every captured tick is negative"

    row = swap_rows[0]
    raw = unsigned_word(row["data"], 4)
    assert raw > 1 << 255, "the sign bit is set on every captured tick"
    assert signed_word(row["data"], 4) == row["tick"]

    # The low three bytes happen to read correctly *because* the word is sign
    # extended, so that is not the failure to guard. Taking the word as written
    # is, and it yields a number no tick could be.
    assert raw - (1 << 256) == row["tick"]


@pytest.mark.trace("REQ-WP-058")
def test_a_payload_of_the_wrong_width_is_refused(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    row = swap_rows[0]
    truncated = row["data"][: 2 + 4 * 64]
    record = _record(
        block=row["block"],
        log_index=row["log_index"],
        address=row["pool"],
        topics=row["topics"],
        data=truncated,
        transaction=row["transaction"],
    )
    with pytest.raises(ValueError, match="five words"):
        decode_swap(record, pools[row["pool"]])


# --------------------------------------------------------------------------
# Section 18.6's registry
# --------------------------------------------------------------------------


def _registry(pools: dict[str, RegisteredPool]) -> tuple[DecoderRegistry, dict[str, RegistryEntry]]:
    registry = DecoderRegistry()
    entries = {}
    for address, pool in pools.items():
        decoder: ProtocolDecoder = SwapDecoder(
            protocol=pool.family, version="1.0.0", pools={address: pool}
        )
        entry = RegistryEntry(
            protocol=pool.family,
            version="1.0.0",
            address=address,
            abi_hash=f"0xabi-{pool.family}",
            from_block=0,
            event_signatures=(SWAP_TOPIC0,),
        )
        registry.register(entry, decoder)
        entries[address] = entry
    return registry, entries


@pytest.mark.trace("REQ-WP-058")
def test_the_registry_attributes_each_swap_to_its_own_protocol(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    registry, _ = _registry(pools)
    seen: Counter[str] = Counter()
    for row in swap_rows:
        events, failure = registry.decode(_swap_record(row))
        assert failure is None
        assert len(events) == 1
        assert events[0].protocol == pools[row["pool"]].family
        seen[events[0].protocol] += 1
    assert seen == Counter({"uniswap_v3": 53, "algebra_integral": 30})


@pytest.mark.trace("REQ-WP-058")
def test_an_algebra_event_carries_no_fee_field(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """A key that is not there cannot be read as a number by a careless consumer."""
    registry, _ = _registry(pools)
    row = next(row for row in swap_rows if pools[row["pool"]].dynamic_fee)
    events, _ = registry.decode(_swap_record(row))
    assert "fee_pips" not in events[0].fields

    other = next(row for row in swap_rows if not pools[row["pool"]].dynamic_fee)
    events, _ = registry.decode(_swap_record(other))
    assert events[0].fields["fee_pips"] == "500"


@pytest.mark.trace("REQ-WP-058")
def test_an_unregistered_pool_decodes_to_nothing(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """130 addresses emit this topic; a decoder keyed on it would decode them all."""
    registry, _ = _registry(pools)
    row = swap_rows[0]
    record = _record(
        block=row["block"],
        log_index=row["log_index"],
        address="0x" + "22" * 20,
        topics=row["topics"],
        data=row["data"],
        transaction=row["transaction"],
    )
    events, failure = registry.decode(record)
    assert events == []
    assert failure is not None
    assert "no registry entry" in failure.reason


@pytest.mark.trace("REQ-WP-058")
def test_a_changed_abi_fails_closed(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    registry, _ = _registry(pools)
    row = swap_rows[0]
    events, failure = registry.decode(_swap_record(row), observed_abi_hash="0xupgraded")
    assert events == []
    assert failure is not None
    assert "failing closed" in failure.reason


# --------------------------------------------------------------------------
# Cross-layer transfers
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-058")
def test_a_system_address_resolves_to_its_core_index() -> None:
    assert core_index_for(f"0x{SYSTEM_BASE:040x}") == 0
    assert core_index_for(f"0x{SYSTEM_BASE + 850:040x}") == 850
    assert core_index_for("0x5555555555555555555555555555555555555555") is None
    assert core_index_for("0x" + "00" * 20) is None
    assert core_index_for("not an address") is None


@pytest.mark.trace("REQ-WP-058")
def test_index_zero_is_an_asset_and_not_an_absence(
    transfer_rows: list[dict[str, Any]], assets: dict[int, CoreAsset]
) -> None:
    """`0x2000…0000` is USDC. A falsy index is not a missing one."""
    assert assets[0].name == "USDC"
    assert any(row["core_index"] == 0 for row in transfer_rows)


@pytest.mark.trace("REQ-WP-058")
def test_every_captured_transfer_resolves_to_the_asset_hypercore_names(
    transfer_rows: list[dict[str, Any]], assets: dict[int, CoreAsset]
) -> None:
    directions: Counter[TransferDirection] = Counter()
    for row in transfer_rows:
        record = _record(
            block=row["block"],
            log_index=row["log_index"],
            address=row["token"],
            topics=row["topics"],
            data=row["data"],
            transaction=row["transaction"],
        )
        transfer = decode_cross_layer_transfer(record, assets)
        assert transfer is not None
        assert transfer.asset.index == row["core_index"]
        assert transfer.asset.name == row["core_name"]
        assert transfer.asset.system_address == row["system_address"]
        assert transfer.evm_amount == int(row["amount"])
        directions[transfer.direction] += 1
    assert directions == Counter({TransferDirection.TO_CORE: 44})


@pytest.mark.trace("REQ-WP-058")
def test_the_credited_amount_uses_the_assets_own_exponent(assets: dict[int, CoreAsset]) -> None:
    """The log's number and HyperCore's number differ by up to ten trillion."""
    usdc = assets[0]
    assert (usdc.evm_extra_wei_decimals, usdc.wei_decimals, usdc.evm_decimals) == (-2, 8, 6)
    assert to_core_amount(299_170_000, usdc) == CoreAmount(core_wei=29_917_000_000, remainder=0)

    purr = next(asset for asset in assets.values() if asset.name == "PURR")
    assert (purr.evm_extra_wei_decimals, purr.wei_decimals, purr.evm_decimals) == (13, 5, 18)
    assert to_core_amount(10**18, purr) == CoreAmount(core_wei=10**5, remainder=0)
    assert to_core_amount(10**18, purr).core_wei != 10**18


@pytest.mark.trace("REQ-WP-058")
def test_dust_below_hypercore_resolution_is_reported_not_dropped(
    assets: dict[int, CoreAsset],
) -> None:
    purr = next(asset for asset in assets.values() if asset.name == "PURR")
    amount = to_core_amount(10**18 + 7, purr)
    assert amount == CoreAmount(core_wei=10**5, remainder=7)
    assert not amount.exact


@pytest.mark.trace("REQ-WP-058")
def test_every_captured_transfer_converted_exactly(
    transfer_rows: list[dict[str, Any]], assets: dict[int, CoreAsset]
) -> None:
    """True of this sample, and asserted so that a sample where it stops is loud."""
    for row in transfer_rows:
        asset = assets[row["core_index"]]
        assert to_core_amount(int(row["amount"]), asset).exact


@pytest.mark.trace("REQ-WP-058")
def test_a_foreign_token_at_a_system_address_is_not_a_cross_layer_transfer(
    transfer_rows: list[dict[str, Any]], assets: dict[int, CoreAsset]
) -> None:
    """Anyone can send any ERC-20 to a system address. That credits nothing."""
    row = transfer_rows[0]
    record = _record(
        block=row["block"],
        log_index=row["log_index"],
        address="0x" + "33" * 20,
        topics=row["topics"],
        data=row["data"],
        transaction=row["transaction"],
    )
    assert decode_cross_layer_transfer(record, assets) is None


@pytest.mark.trace("REQ-WP-058")
def test_an_ordinary_transfer_is_not_a_cross_layer_transfer(
    swap_rows: list[dict[str, Any]], assets: dict[int, CoreAsset]
) -> None:
    row = next(row for row in swap_rows if row["transfers"])
    for record in _transfer_records(row):
        assert decode_cross_layer_transfer(record, assets) is None


# --------------------------------------------------------------------------
# What the sweep found nothing asserting
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-058")
def test_the_sign_bit_is_the_top_bit() -> None:
    """No captured word lands between 2^254 and 2^255, so only this says where
    the boundary is. A threshold one bit low reads a large positive amount as a
    negative one, and every real amount is far too small to notice."""
    assert signed_word(f"0x{(1 << 255) - 1:064x}", 0) == (1 << 255) - 1
    assert signed_word(f"0x{1 << 255:064x}", 0) == -(1 << 255)
    assert signed_word(f"0x{1 << 254:064x}", 0) == 1 << 254
    assert signed_word(f"0x{(1 << 256) - 1:064x}", 0) == -1


@pytest.mark.trace("REQ-WP-058")
def test_a_disagreeing_transfer_is_a_mismatch() -> None:
    """Every captured swap agrees, so nothing else ever builds a disagreement."""
    flow = TokenFlow(token="0xtoken", amount=41, log_index=3)
    assert settlement_of(42, flow) is Settlement.MISMATCHED
    assert settlement_of(42, None) is Settlement.MISMATCHED
    assert settlement_of(42, TokenFlow(token="0xtoken", amount=42, log_index=3)) is (
        Settlement.MATCHED
    )
    assert settlement_of(-42, TokenFlow(token="0xtoken", amount=42, log_index=3)) is (
        Settlement.MISMATCHED
    ), "a sign flip is a mismatch, not a magnitude"


@pytest.mark.trace("REQ-WP-058")
def test_a_transfer_out_of_a_system_address_moves_toward_hyperevm(
    assets: dict[int, CoreAsset],
) -> None:
    """Definitional, not measured: all 44 captured transfers move to HyperCore,
    so this direction has no fixture behind it and says so."""
    usdc = assets[0]
    holder = "0x" + "44" * 20
    record = _record(
        block=1,
        log_index=0,
        address=usdc.evm_contract,
        topics=[
            TRANSFER_TOPIC0,
            f"0x{SYSTEM_BASE + usdc.index:064x}",
            f"0x{int(holder, 16):064x}",
        ],
        data=f"0x{1_000_000:064x}",
        transaction="0xtx",
    )
    transfer = decode_cross_layer_transfer(record, assets)
    assert transfer is not None
    assert transfer.direction is TransferDirection.TO_EVM
    assert transfer.counterparty == holder
    assert transfer.asset.name == "USDC"


@pytest.mark.trace("REQ-WP-058")
def test_a_decoder_refuses_a_pool_of_another_family(
    pools: dict[str, RegisteredPool],
) -> None:
    """The guarantee the requirement is named for: the protocol comes from the
    registry. One decoder per family, and each holds only its own pools."""
    algebra = next(pool for pool in pools.values() if pool.dynamic_fee)
    uniswap = next(pool for pool in pools.values() if not pool.dynamic_fee)
    impostor = SwapDecoder(
        protocol=PoolFamily.UNISWAP_V3, version="1.0.0", pools={algebra.address: algebra}
    )
    entry = RegistryEntry(
        protocol=PoolFamily.UNISWAP_V3,
        version="1.0.0",
        address=algebra.address,
        abi_hash="0xabi",
        from_block=0,
    )
    record = _record(
        block=1,
        log_index=0,
        address=algebra.address,
        topics=[SWAP_TOPIC0, f"0x{0:064x}", f"0x{0:064x}"],
        data="0x" + "00" * 160,
        transaction="0xtx",
    )
    assert impostor.matches(record, entry) is False

    honest = SwapDecoder(
        protocol=PoolFamily.UNISWAP_V3, version="1.0.0", pools={uniswap.address: uniswap}
    )
    assert honest.matches(
        _record(
            block=1,
            log_index=0,
            address=uniswap.address,
            topics=[SWAP_TOPIC0, f"0x{0:064x}", f"0x{0:064x}"],
            data="0x" + "00" * 160,
            transaction="0xtx",
        ),
        RegistryEntry(
            protocol=PoolFamily.UNISWAP_V3,
            version="1.0.0",
            address=uniswap.address,
            abi_hash="0xabi",
            from_block=0,
        ),
    )


@pytest.mark.trace("REQ-WP-058")
def test_the_registry_declines_a_log_that_is_not_a_swap(
    swap_rows: list[dict[str, Any]], pools: dict[str, RegisteredPool]
) -> None:
    """An Algebra pool emits a `Fee` for every swap, so half the logs arriving
    from that address are not swaps at all."""
    registry, _ = _registry(pools)
    row = next(row for row in swap_rows if row["fee_pips"] is not None)
    fee_log = _record(
        block=row["block"],
        log_index=row["fee_log_index"],
        address=row["pool"],
        topics=[FEE_TOPIC0],
        data=f"0x{row['fee_pips']:064x}",
        transaction=row["transaction"],
    )
    events, failure = registry.decode(fee_log)
    assert events == []
    assert failure is not None
    assert "no decoder matched" in failure.reason
