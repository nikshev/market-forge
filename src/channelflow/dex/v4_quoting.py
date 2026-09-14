"""Uniswap v4 `CUSTOM_ACCOUNTING` pools are priced by quoting them, not by a curve.

# @trace: REQ-WP-071

PRD section 18.8.1 gives these pools one rule: *"do not assume the standard
curve; prefer executable quoting/simulation adapter."* [[REQ-WP-047]] built the
classification. This is the quote.

**Why the curve cannot be trusted here, measured.** At Ethereum mainnet block
25975796, three of the four `CUSTOM_ACCOUNTING` pools in
`tests/fixtures/uniswap_v4/` hold **zero** liquidity in the manager. A tick
traversal reads that and reports that the pool cannot be moved at any size. Two
of those three absorb a whole ether -- one of them returning
496412035653451820217981817 units for it. The liquidity is in the hook, and the
manager's tick map does not know it exists. The fourth pool holds real
liquidity, so the class alone does not say which case you are in: only the quote
does.

**A refusal is an answer.** Every refusal the chain gave arrived wrapped in
`UnexpectedRevertBytes(bytes)` with a named reason inside -- one pool refusing
at every rung of the ladder, and two pools quoting one direction while refusing
to buy back the exact amount they had just offered. So on two of these four
pools a mid price does not exist, and a number that split the difference would
be manufactured here rather than measured on the chain.

Nothing in this module retries at a smaller size, falls back to another block,
or renders a refusal as zero. Each of those would turn a refusal into a number
that is positive, ordered and believable.

**Selectors are computed, never copied.** A selector is the Keccak-256 of a
signature, so deriving it from the signature turns a typo into a failed call
rather than a wrong one. `hashlib.sha3_256` is *not* this -- SHA-3 and Keccak
differ in their padding, and the wrong one yields plausible hashes rather than
an error.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from eth_hash.auto import keccak

from channelflow.chain.providers import CallReverted
from channelflow.dex.uniswap_v4 import PoolKey, PoolRegistry, RoutingKey

_UINT256 = (1 << 256) - 1
_ADDRESS_MASK = (1 << 160) - 1
_WORD = 64  # hex characters


def selector(signature: str) -> str:
    """The four-byte selector of a Solidity signature."""
    return "0x" + keccak(signature.encode())[:4].hex()


QUOTE_EXACT_INPUT_SINGLE = (
    "quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))"
)

QUOTE_SELECTOR = selector(QUOTE_EXACT_INPUT_SINGLE)
POOL_MANAGER_SELECTOR = selector("poolManager()")

#: The quoter wraps whatever the pool or the manager reverted with. One layer,
#: always -- measured on every refusal in the capture.
UNEXPECTED_REVERT_BYTES = selector("UnexpectedRevertBytes(bytes)")


class RefusalReason(StrEnum):
    """Why the contract refused, where it said so by name."""

    NOT_ENOUGH_LIQUIDITY = "NOT_ENOUGH_LIQUIDITY"
    PRICE_LIMIT_ALREADY_EXCEEDED = "PRICE_LIMIT_ALREADY_EXCEEDED"
    UNKNOWN = "UNKNOWN"


#: Inner error signatures, by the reason they mean. An unrecognised selector
#: gives `UNKNOWN` and keeps its payload: an unknown reason is not a missing
#: one, and must never collapse into a recognised one.
_REASONS: dict[str, tuple[RefusalReason, int]] = {
    selector("NotEnoughLiquidity(bytes32)"): (RefusalReason.NOT_ENOUGH_LIQUIDITY, 1),
    selector("PriceLimitAlreadyExceeded(uint160,uint160)"): (
        RefusalReason.PRICE_LIMIT_ALREADY_EXCEEDED,
        2,
    ),
}


class QuoteRefused(RuntimeError):
    """The contract refused to quote. A fact about the pool, not the endpoint."""

    def __init__(
        self,
        request: QuoteRequest,
        *,
        reason: RefusalReason,
        raw: str | None,
        named_pool_id: str | None = None,
        arguments: tuple[int, ...] = (),
    ) -> None:
        super().__init__(
            f"{request.route.pool_id} refused {request.exact_amount} "
            f"{'0->1' if request.zero_for_one else '1->0'}: {reason.value}"
        )
        self.request = request
        self.reason = reason
        self.raw = raw
        self.named_pool_id = named_pool_id
        self.arguments = arguments


class QuoteUnavailable(RuntimeError):
    """The call did not reach a verdict. A fact about the endpoint.

    Deliberately unrelated to `QuoteRefused` by inheritance in either direction:
    a caller that caught one and meant the other would read "this pool has no
    depth" off a node that was merely busy.
    """


class NoTwoSidedMarket(ValueError):
    """A mid was asked for and one direction refused.

    Measured on two of the four pools in the fixture. Halving a one-sided price,
    or passing it off as a mid, invents the half that does not exist.
    """


class WrongQuoter(ValueError):
    """The quoter does not name the manager the pool was routed under."""


@dataclass(frozen=True)
class QuoteRequest:
    """What is being asked: a pool, a direction, and a size."""

    route: RoutingKey
    zero_for_one: bool
    #: Exact **input**, in the input currency's smallest unit.
    exact_amount: int

    def __post_init__(self) -> None:
        if self.exact_amount <= 0:
            raise ValueError(f"exact_amount must be positive, got {self.exact_amount}")


@dataclass(frozen=True)
class Quote:
    """An executable answer, true at one block and for one size."""

    request: QuoteRequest
    block: int
    amount_out: int
    gas_estimate: int

    def __post_init__(self) -> None:
        if self.amount_out <= 0:
            raise ValueError(
                f"amount_out must be positive, got {self.amount_out}; a quoter that "
                "returns zero without reverting has not quoted"
            )


def implied_price(quote: Quote) -> Decimal:
    """`currency1` per `currency0`, whichever way the quote was taken.

    Inverted for `one_for_zero` so two quotes on one pool are comparable. The
    two are *not* reciprocal -- the gap between them is the round trip cost, and
    on the fixture's two-sided pool it is 1.93%.
    """
    amount_in = Decimal(quote.request.exact_amount)
    amount_out = Decimal(quote.amount_out)
    if quote.request.zero_for_one:
        return amount_out / amount_in
    return amount_in / amount_out


def _word(value: int) -> str:
    return f"{value & _UINT256:064x}"


def encode_exact_input_single(key: PoolKey, *, zero_for_one: bool, exact_amount: int) -> str:
    """`QuoteExactSingleParams` as call data.

    The struct holds a `bytes` member, so it is dynamic and the call data opens
    with an offset to it. The `PoolKey` is static and inlines as five whole
    words -- `int24 tickSpacing` sign-extended across all 256 bits, so a spacing
    of -1 contributes `0xff…ff`. Packing it, or extending the sign wrongly,
    produces call data that reverts rather than one that quotes a different
    pool, which is why one working call is evidence of the layout.
    """
    body = (
        _word(int(key.currency0, 16) & _ADDRESS_MASK)
        + _word(int(key.currency1, 16) & _ADDRESS_MASK)
        + _word(key.fee)
        + _word(key.tick_spacing)
        + _word(int(key.hooks, 16) & _ADDRESS_MASK)
        + _word(1 if zero_for_one else 0)
        + _word(exact_amount)
        + _word(8 * 32)  # offset to hookData, from the start of the tuple
        + _word(0)  # hookData length: empty
    )
    return QUOTE_SELECTOR + _word(32) + body


def decode_refusal(payload: str | None) -> tuple[RefusalReason, str | None, tuple[int, ...]]:
    """The reason inside `UnexpectedRevertBytes`, where one can be read.

    Returns `UNKNOWN` for anything it cannot read -- a payload the endpoint
    never sent, one that is not a wrapper, one whose inner selector is
    unrecognised, one truncated mid-word. Every one of those is a refusal whose
    reason is unknown, and none of them is a different refusal.
    """
    unreadable = (RefusalReason.UNKNOWN, None, ())
    if payload is None or not payload.startswith("0x"):
        return unreadable
    body = payload[2:]
    if not body.startswith(UNEXPECTED_REVERT_BYTES[2:]):
        return unreadable
    try:
        offset = int(body[8 : 8 + _WORD], 16)
        head = 8 + offset * 2
        length = int(body[head : head + _WORD], 16)
        inner = body[head + _WORD : head + _WORD + length * 2]
    except ValueError:
        return unreadable
    if len(inner) < 8:
        return unreadable
    known = _REASONS.get("0x" + inner[:8])
    if known is None:
        return (RefusalReason.UNKNOWN, None, ())
    reason, arity = known
    args = inner[8:]
    if len(args) < arity * _WORD:
        return unreadable
    words = tuple(int(args[i * _WORD : (i + 1) * _WORD], 16) for i in range(arity))
    named = "0x" + args[:_WORD] if reason is RefusalReason.NOT_ENOUGH_LIQUIDITY else None
    return (reason, named, words)


class _Provider(Protocol):
    """The slice of `ChainDataProvider` this adapter uses."""

    def eth_call(self, *, to: str, data: str, block: int) -> str: ...


class ExecutableQuoter:
    """Prices a v4 pool by asking a quoter contract, at one fixed block.

    Named for what it does rather than for the contract it calls: that contract
    is already called `V4Quoter`, and one name for two things in one module is
    how a reader ends up reasoning about the wrong one.
    """

    def __init__(
        self,
        provider: _Provider,
        registry: PoolRegistry,
        *,
        address: str,
        pool_manager: str,
        block: int,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self.address = address.lower()
        self.pool_manager = pool_manager.lower()
        self.block = block

    def verify(self) -> None:
        """Refuse a quoter that does not name our manager.

        Called once by whoever builds the adapter. Not from the constructor: a
        constructor that does I/O cannot be built in a test without a provider,
        and not on first use either, because a check that happens implicitly is
        a check nobody can see happening.
        """
        named = "0x" + self._call(self.address, POOL_MANAGER_SELECTOR)[-40:]
        if named.lower() != self.pool_manager:
            raise WrongQuoter(
                f"quoter {self.address} names manager {named}, but the pool is routed "
                f"under {self.pool_manager}; quoting it would price a different chain's pool"
            )

    def quote(self, request: QuoteRequest) -> Quote:
        """One call, one answer. No retry, no fallback, no smaller size."""
        _, key = self._registry.route(
            chain_id=request.route.chain_id,
            pool_manager=request.route.pool_manager,
            pool_id=request.route.pool_id,
        )
        data = encode_exact_input_single(
            key, zero_for_one=request.zero_for_one, exact_amount=request.exact_amount
        )
        try:
            returned = self._call(self.address, data)
        except CallReverted as reverted:
            reason, named, arguments = decode_refusal(reverted.data)
            raise QuoteRefused(
                request,
                reason=reason,
                raw=reverted.data,
                named_pool_id=named,
                arguments=arguments,
            ) from reverted
        body = returned[2:]
        if len(body) < 2 * _WORD:
            raise QuoteUnavailable(
                f"quoter returned {len(body) // 2} bytes for {request.route.pool_id}; "
                "a short return is not a quote of what fits in it"
            )
        return Quote(
            request=request,
            block=self.block,
            amount_out=int(body[:_WORD], 16),
            gas_estimate=int(body[_WORD : 2 * _WORD], 16),
        )

    def mid(self, route: RoutingKey, *, size: int) -> Decimal:
        """The geometric mean of both directions, or nothing at all.

        The reverse leg is quoted at what the forward leg returned, so the pair
        is a round trip of a real amount rather than of a number chosen here.
        """
        try:
            buy = self.quote(QuoteRequest(route=route, zero_for_one=True, exact_amount=size))
            sell = self.quote(
                QuoteRequest(route=route, zero_for_one=False, exact_amount=buy.amount_out)
            )
        except QuoteRefused as refused:
            raise NoTwoSidedMarket(
                f"{route.pool_id} refused {'0->1' if refused.request.zero_for_one else '1->0'} "
                f"({refused.reason.value}), so it has one side and no mid"
            ) from refused
        return (implied_price(buy) * implied_price(sell)).sqrt()

    def _call(self, to: str, data: str) -> str:
        try:
            return self._provider.eth_call(to=to, data=data, block=self.block)
        except CallReverted:
            raise
        except (LookupError, NotImplementedError):
            # The provider is telling us it holds no answer, which is its own
            # business and never a verdict about the pool.
            raise
        except Exception as failure:  # noqa: BLE001
            raise QuoteUnavailable(f"{to} {data[:10]} at {self.block}: {failure}") from failure
