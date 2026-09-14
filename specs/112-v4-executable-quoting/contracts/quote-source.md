# Contract: quoting a v4 pool

## Provider (existing, extended)

```python
class ChainDataProvider(Protocol):
    name: str
    def get_block(self, number: int) -> dict[str, Any]: ...
    def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]: ...
    def eth_call(self, *, to: str, data: str, block: int) -> str: ...
```

Added: `CallReverted(RuntimeError)` with `.data: str | None`. A provider raises
it when the node reports a contract revert, carrying the payload where the node
sent one and `None` where it did not. `None` means "this endpoint did not say",
not "the contract reverted with nothing" — the distinction the capture tooling
already draws.

## Adapter

```python
class V4Quoter:
    def __init__(self, provider: ChainDataProvider, *, address: str,
                 pool_manager: str, block: int) -> None: ...
    def verify(self) -> None: ...                       # raises WrongQuoter
    def quote(self, request: QuoteRequest) -> Quote: ...  # raises QuoteRefused / QuoteUnavailable
    def mid(self, route: RoutingKey, *, size: int) -> Decimal: ...  # raises NoTwoSidedMarket
```

`quote` needs the pool's `PoolKey` to encode the call — the id is a hash. It
takes a `PoolRegistry` at construction and resolves the route through it, so an
unknown pool raises `UnknownPool` exactly as every other v4 path does.

`verify()` is not optional and not automatic-on-first-use: it is called once by
whoever constructs the adapter, and a caller that skips it gets quotes from a
contract nobody checked. The constructor does not call it, because a constructor
that does I/O cannot be built in a test without a provider.

## Ordering guarantees

- `quote` never retries at another size.
- `quote` never falls back to another block.
- `mid` issues exactly two quotes, both at the adapter's block, and propagates
  the first refusal as the cause of `NoTwoSidedMarket`.
