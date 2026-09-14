# Quickstart — validating REQ-WP-071

No services and no network. The fixture is the chain.

## Run it

```bash
make test-fast                     # the whole unit suite
.venv/bin/pytest tests/unit/dex/test_v4_quoting.py -v
```

## What proves the requirement

| Scenario | Expected |
|---|---|
| `depth_to_bps` on pool `0xf7caa8ee…`'s state | `reachable=False, amount0=0` with "no active liquidity" — the wrong answer, asserted so the regression is visible |
| `require_curve_applies` on each of the four fixture pools | raises `CurveDoesNotApply` |
| `require_curve_applies` on a `STANDARD_CL` key | returns |
| quote `0xf7caa8ee…`, `zero_for_one`, 1e18 | `amount_out == 496412035653451820217981817` |
| quote `0x5ce617f9…` at each of the four sizes | `QuoteRefused`, reason `NOT_ENOUGH_LIQUIDITY`, `named_pool_id == 0x5ce617f9…` |
| quote `0x5d10cbe0…` in reverse | `QuoteRefused`, reason `PRICE_LIMIT_ALREADY_EXCEEDED` |
| `mid` on `0xf7caa8ee…` | `NoTwoSidedMarket`, `__cause__` is the refusal |
| `mid` on `0x88249e68…` | a `Decimal`, from two real quotes |
| a quoter naming a different manager | `WrongQuoter`, before any quote |
| a provider that raises a transport error | `QuoteUnavailable`, never `QuoteRefused` |
| a request absent from the fixture | `QuoteNotCaptured`, never `amount_out == 0` |

## Refreshing the fixture

Deliberate and manual, like every other chain fixture here:

```bash
.venv/bin/python -m tools.record.v4_quote_capture
```

It re-verifies both contracts against the manager before recording anything, and
the recorded block moves. Expect the asserted amounts to change and update them
from the run — they are the chain's numbers, not ours.
