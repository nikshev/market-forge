"""PRD section 18.11.2's HyperEVM pool events and cross-layer transfers.

# @trace: REQ-WP-058

    "A HyperEVM AMM is analyzed according to **its AMM protocol**, not according
    to the Hyperliquid CLOB model."

[[REQ-WP-014]] built section 18.6's registry and nothing was ever registered in
it. These are the first concrete decoders, and chain 999 is why the sentence
above is a requirement rather than a truism: its two busiest WHYPE/USDC pools
emit the **identical** `Swap` topic0 with the identical five-word payload and
belong to different protocols. One is a Uniswap v3 factory whose `fee()` never
changes; the other is Algebra Integral, whose fee is chosen per swap by a
plugin and published as a separate `Fee(uint16)` log.

Measured over 900 blocks on 2026-09-12: the Algebra pool's `fee()` at the end
of the window is 1073, and its fourteen swaps carry 1075, 1076, 1077 and 1078.
Pricing any of them from the pool's current fee is wrong by less than half a
percent -- which is to say, wrong and believable.

So **the protocol comes from the registry, never from the event**, and **a fee
nobody published is absent, not zero and not the pool's current one**.

The cross-layer half fails the same way. A HyperCore transfer is an ordinary
ERC-20 `Transfer` whose counterparty is a code-less address
`0x2000...0000 + index`; the index is the HyperCore spot index, and the amount
is in EVM units. HyperCore credits it divided by `10^evm_extra_wei_decimals`,
which spans -2 to +13 across the 170 spot assets that have an EVM contract.
Reading the log's amount as the credited amount is wrong by up to ten trillion
and is a positive balance either way.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from eth_hash.auto import keccak

from channelflow.chain.decoders import ProtocolEvent, RegistryEntry
from channelflow.chain.records import ChainRecord


def event_topic(signature: str) -> str:
    """Keccak-256 of an event signature.

    Computed, never transcribed: a typo then costs a topic that matches nothing
    rather than one that matches the wrong thing.
    """
    return "0x" + keccak(signature.encode()).hex()


SWAP_SIGNATURE = "Swap(address,address,int256,int256,uint160,uint128,int24)"
FEE_SIGNATURE = "Fee(uint16)"
TRANSFER_SIGNATURE = "Transfer(address,address,uint256)"

#: Shared by both families. This constant existing once, for two protocols, is
#: the whole point of the module.
SWAP_TOPIC0 = event_topic(SWAP_SIGNATURE)
FEE_TOPIC0 = event_topic(FEE_SIGNATURE)
TRANSFER_TOPIC0 = event_topic(TRANSFER_SIGNATURE)

#: Hyperliquid's chain id.
CHAIN_ID = 999

#: Fees on both families are in pips: millionths, so 500 is five basis points.
PIPS = 1_000_000

#: Where HyperCore's spot assets appear on HyperEVM. The index is the
#: difference from the base, not the address read as an integer.
SYSTEM_BASE = 0x2000000000000000000000000000000000000000

#: The last index the prefix can express before the address stops looking like
#: a system address. 501 spot assets exist today; the ceiling is the width of
#: the low bits the convention leaves free.
SYSTEM_INDEX_CEILING = 1 << 32


class PoolFamily(StrEnum):
    """The two AMM protocols measured on chain 999."""

    UNISWAP_V3 = "uniswap_v3"
    ALGEBRA_INTEGRAL = "algebra_integral"


class UnknownFactory(LookupError):
    """A factory no measurement covers.

    Refused rather than defaulted: the whole failure this module exists to
    prevent is a pool decoded as the family it resembles.
    """


class FeeNotPublished(LookupError):
    """A fee was asked of a swap whose fee log was never supplied."""


#: The factories measured on chain 999 on 2026-09-12, by which state call their
#: pools answer. Algebra pools answer `globalState()` and `plugin()`; Uniswap
#: v3 pools answer `slot0()`. Both answer `fee()`, and that is the trap.
FACTORIES: Mapping[str, PoolFamily] = {
    "0xff7b3e8c00e57ea31477c32a5b52a58eea47b072": PoolFamily.UNISWAP_V3,
    "0xf77bd082c627aa54591cf2f2eaa811fd1ab3b1f3": PoolFamily.ALGEBRA_INTEGRAL,
}

#: Which families publish a fee per swap. A family that does cannot be priced
#: from pool configuration at all, so this drives `RegisteredPool` rather than
#: being a note about it.
DYNAMIC_FEE_FAMILIES = frozenset({PoolFamily.ALGEBRA_INTEGRAL})


def family_for(factory: str) -> PoolFamily:
    """The protocol a factory deploys, or a refusal."""
    family = FACTORIES.get(factory.lower())
    if family is None:
        raise UnknownFactory(
            f"factory {factory} is not a measured HyperEVM DEX factory; a pool "
            "cannot be decoded as the family it resembles"
        )
    return family


@dataclass(frozen=True)
class RegisteredPool:
    """One pool, and what is fixed about it.

    `fee_pips` is `None` for a dynamic-fee family. That is not a missing value
    to fill in later -- there is no such number for those pools, and a field
    that held one would be a place for the wrong answer to live.
    """

    address: str
    family: PoolFamily
    factory: str
    token0: str
    token1: str
    tick_spacing: int
    fee_pips: int | None = None

    def __post_init__(self) -> None:
        if self.family in DYNAMIC_FEE_FAMILIES and self.fee_pips is not None:
            raise ValueError(
                f"{self.address} is {self.family}, whose fee is set per swap; a "
                f"pool-level fee of {self.fee_pips} would be applied to swaps "
                "that were charged something else"
            )
        if self.family not in DYNAMIC_FEE_FAMILIES and self.fee_pips is None:
            raise ValueError(
                f"{self.address} is {self.family}, whose fee is immutable and must be recorded"
            )

    @property
    def dynamic_fee(self) -> bool:
        return self.family in DYNAMIC_FEE_FAMILIES


@dataclass(frozen=True)
class HyperEvmSwap:
    """One decoded swap.

    `amount0` and `amount1` are signed from the pool's side: positive is into
    the pool. Both are checkable against the transaction's own ERC-20 transfers
    without an archive node, which on this chain is the only check there is
    (ADR-067).
    """

    pool: str
    family: PoolFamily
    sender: str
    recipient: str
    amount0: int
    amount1: int
    sqrt_price_x96: int
    liquidity: int
    tick: int
    fee_pips: int | None = None

    @property
    def fee(self) -> int:
        """The fee charged, or a refusal.

        A property rather than a defaulting getter: every caller that wants a
        number has to say what it does when there is not one.
        """
        if self.fee_pips is None:
            raise FeeNotPublished(
                f"{self.family} publishes a fee per swap and none was supplied "
                f"for the swap on {self.pool}; the pool's current fee is a "
                "different number"
            )
        return self.fee_pips

    def with_fee(self, fee_pips: int) -> HyperEvmSwap:
        if fee_pips < 0 or fee_pips >= PIPS:
            raise ValueError(f"fee {fee_pips} is not a fraction of {PIPS}")
        return HyperEvmSwap(**{**vars(self), "fee_pips": fee_pips})


def signed_word(data: str, index: int) -> int:
    """One ABI word, read as a two's-complement 256-bit integer.

    Every signed field in these events -- `int256` amounts and the `int24` tick
    alike -- arrives sign-extended across a full word. Reading the tick as a
    24-bit two's complement of its low bytes turns -232481 into 16544735: a
    tick, in range, and wrong.
    """
    body = data.removeprefix("0x")
    word = int(body[index * 64 : (index + 1) * 64], 16)
    return word - (1 << 256) if word >= (1 << 255) else word


def unsigned_word(data: str, index: int) -> int:
    body = data.removeprefix("0x")
    return int(body[index * 64 : (index + 1) * 64], 16)


def topic_address(topic: str) -> str:
    return "0x" + topic.removeprefix("0x")[-40:].lower()


def decode_swap(record: ChainRecord, pool: RegisteredPool) -> HyperEvmSwap:
    """The payload both families share, attributed to the family the pool is.

    The fee comes from the pool only where the pool has one. For Algebra it
    stays absent here and is supplied by `pair_fees`, because the log that
    carries it is a different log.
    """
    if record.topic0 != SWAP_TOPIC0:
        raise ValueError(f"{record.topic0} is not a HyperEVM swap")
    if len(record.topics) != 3:
        raise ValueError(f"a swap carries a sender and a recipient topic; got {len(record.topics)}")
    body = record.data.removeprefix("0x")
    if len(body) != 5 * 64:
        raise ValueError(
            f"a swap payload is five words; got {len(body) / 64:g} on {record.address}"
        )
    return HyperEvmSwap(
        pool=pool.address,
        family=pool.family,
        sender=topic_address(record.topics[1]),
        recipient=topic_address(record.topics[2]),
        amount0=signed_word(record.data, 0),
        amount1=signed_word(record.data, 1),
        sqrt_price_x96=unsigned_word(record.data, 2),
        liquidity=unsigned_word(record.data, 3),
        tick=signed_word(record.data, 4),
        fee_pips=pool.fee_pips,
    )


def decode_fee(record: ChainRecord) -> int:
    """The `Fee(uint16)` a plugin published for the swap that follows it."""
    if record.topic0 != FEE_TOPIC0:
        raise ValueError(f"{record.topic0} is not a fee publication")
    return unsigned_word(record.data, 0)


@dataclass(frozen=True)
class SwapDecoder:
    """PRD section 18.6's `ProtocolDecoder`, for one family.

    One class for both families rather than two, because the payload is
    genuinely identical -- what differs is which pools it will accept and where
    a fee comes from, and both of those are data.
    """

    protocol: str
    version: str
    pools: Mapping[str, RegisteredPool]

    def matches(self, record: ChainRecord, entry: RegistryEntry) -> bool:
        pool = self.pools.get(record.address.lower())
        return (
            record.topic0 == SWAP_TOPIC0
            and pool is not None
            and pool.family == self.protocol
            and entry.protocol == self.protocol
        )

    def decode(self, record: ChainRecord, entry: RegistryEntry) -> list[ProtocolEvent]:
        pool = self.pools[record.address.lower()]
        swap = decode_swap(record, pool)
        fields = {
            "amount0": str(swap.amount0),
            "amount1": str(swap.amount1),
            "sqrt_price_x96": str(swap.sqrt_price_x96),
            "liquidity": str(swap.liquidity),
            "tick": str(swap.tick),
            "sender": swap.sender,
            "recipient": swap.recipient,
            "token0": pool.token0,
            "token1": pool.token1,
            "tick_spacing": str(pool.tick_spacing),
        }
        if swap.fee_pips is not None:
            # Absent rather than "unknown" or 0: a key that is not there cannot
            # be read as a number by a consumer that forgot to check.
            fields["fee_pips"] = str(swap.fee_pips)
        return [
            ProtocolEvent(
                protocol=entry.protocol,
                version=entry.version,
                name="Swap",
                address=pool.address,
                fields=fields,
                source=record,
            )
        ]


def pair_fees(records: Iterable[ChainRecord]) -> dict[int, int]:
    """Which fee applies to each swap, by log index, within one transaction.

    The plugin publishes a `Fee` before each swap it prices, so the fee for a
    swap is the **last** one preceding it. Positional, and not a fixed offset:
    across the 30 captured Algebra swaps the gap is 3, 6, 7 or 10 log indices,
    depending on what else the transaction did in between.
    """
    ordered = sorted(records, key=lambda record: record.log_index)
    paired: dict[int, int] = {}
    latest: int | None = None
    for record in ordered:
        if record.topic0 == FEE_TOPIC0:
            latest = decode_fee(record)
        elif record.topic0 == SWAP_TOPIC0 and latest is not None:
            paired[record.log_index] = latest
    return paired


@dataclass(frozen=True)
class TokenFlow:
    """A pool's net movement of one token, from the transfers of one transaction."""

    token: str
    amount: int
    log_index: int


def settling_transfer(
    *, pool: str, token: str, swap_log_index: int, transfers: Iterable[ChainRecord]
) -> TokenFlow | None:
    """The transfer that settles one side of a swap (ADR-067).

    The nearest **preceding** transfer of that token involving the pool. Not the
    transaction's net: four of the 103 captured swaps sit in transactions where
    the same pool also flashes or collects, and netting the receipt disagrees
    with the event by orders of magnitude.
    """
    pool = pool.lower()
    best: TokenFlow | None = None
    for record in transfers:
        if record.topic0 != TRANSFER_TOPIC0 or len(record.topics) != 3:
            continue
        if record.address.lower() != token.lower():
            continue
        if record.log_index >= swap_log_index:
            continue
        sender, recipient = topic_address(record.topics[1]), topic_address(record.topics[2])
        if pool not in (sender, recipient):
            continue
        value = unsigned_word(record.data, 0)
        amount = value if recipient == pool else -value
        if best is None or record.log_index > best.log_index:
            best = TokenFlow(token=token, amount=amount, log_index=record.log_index)
    return best


class Settlement(StrEnum):
    """Whether a swap's side agrees with the transfer that settled it."""

    MATCHED = "matched"
    #: The event moved nothing, so no transfer exists to match. Two of the 83
    #: captured swaps have a zero side -- token0 paid in and nothing out. A
    #: check that quietly accepted the nearest preceding transfer here would be
    #: comparing against the *previous* operation's transfer, and would have
    #: reported a mismatch of a plausible size.
    ZERO_SIDE = "zero_side"
    MISMATCHED = "mismatched"


def settlement_of(amount: int, flow: TokenFlow | None) -> Settlement:
    """Compare one side of a swap against the transfer that settled it."""
    if amount == 0:
        return Settlement.ZERO_SIDE
    if flow is not None and flow.amount == amount:
        return Settlement.MATCHED
    return Settlement.MISMATCHED


def core_index_for(address: str) -> int | None:
    """The HyperCore spot index a system address names, or nothing.

    `None` rather than a raise, because most addresses are not system addresses
    and asking is the normal case. `0x2000...0000` is index 0 -- USDC, a real
    asset -- so a falsy index is not an absent one.
    """
    try:
        value = int(address, 16)
    except ValueError:
        return None
    index = value - SYSTEM_BASE
    if index < 0 or index >= SYSTEM_INDEX_CEILING:
        return None
    return index


@dataclass(frozen=True)
class CoreAsset:
    """A HyperCore spot asset with an EVM contract, as `spotMeta` describes it."""

    name: str
    index: int
    evm_contract: str
    evm_extra_wei_decimals: int
    wei_decimals: int

    @property
    def evm_decimals(self) -> int:
        return self.wei_decimals + self.evm_extra_wei_decimals

    @property
    def system_address(self) -> str:
        return f"0x{SYSTEM_BASE + self.index:040x}"


@dataclass(frozen=True)
class CoreAmount:
    """An EVM amount as HyperCore sees it.

    `remainder` is EVM wei below HyperCore's resolution. It was zero in all 90
    captured transfers, which is a fact about the sample and not a guarantee:
    the field exists so that a transfer that does carry dust cannot be rounded
    into agreement.
    """

    core_wei: int
    remainder: int

    @property
    def exact(self) -> bool:
        return self.remainder == 0


def to_core_amount(evm_amount: int, asset: CoreAsset) -> CoreAmount:
    """Convert an EVM transfer amount to the amount HyperCore credits."""
    extra = asset.evm_extra_wei_decimals
    if extra >= 0:
        core_wei, remainder = divmod(evm_amount, 10**extra)
        return CoreAmount(core_wei=core_wei, remainder=remainder)
    # A negative extra means the EVM side carries *fewer* decimals, so nothing
    # can be lost and there is no remainder to report.
    return CoreAmount(core_wei=evm_amount * 10**-extra, remainder=0)


class TransferDirection(StrEnum):
    TO_CORE = "to_core"
    TO_EVM = "to_evm"


@dataclass(frozen=True)
class CrossLayerTransfer:
    """PRD section 18.11.2's HyperCore-HyperEVM transfer event."""

    asset: CoreAsset
    direction: TransferDirection
    counterparty: str
    evm_amount: int
    credited: CoreAmount


def decode_cross_layer_transfer(
    record: ChainRecord, assets: Mapping[int, CoreAsset]
) -> CrossLayerTransfer | None:
    """A transfer to or from a system address, or nothing.

    Returns `None` for the overwhelming majority of transfers, which are
    ordinary. A transfer whose system address names an index no asset table
    covers is also `None`: an index is not an asset.
    """
    if record.topic0 != TRANSFER_TOPIC0 or len(record.topics) != 3:
        return None
    sender, recipient = topic_address(record.topics[1]), topic_address(record.topics[2])
    to_index, from_index = core_index_for(recipient), core_index_for(sender)
    if to_index is not None:
        index, direction, counterparty = to_index, TransferDirection.TO_CORE, sender
    elif from_index is not None:
        index, direction, counterparty = from_index, TransferDirection.TO_EVM, recipient
    else:
        return None
    asset = assets.get(index)
    if asset is None or asset.evm_contract.lower() != record.address.lower():
        return None
    amount = unsigned_word(record.data, 0)
    return CrossLayerTransfer(
        asset=asset,
        direction=direction,
        counterparty=counterparty,
        evm_amount=amount,
        credited=to_core_amount(amount, asset),
    )
