# Phase 1 — Data model

All amounts are integers in the currency's own smallest unit. Nothing here holds
a float.

## `QuoteRequest` (frozen)

| field | type | meaning |
|---|---|---|
| `route` | `RoutingKey` | `(chain_id, pool_manager, pool_id)` — §18.8.2's key, reused unchanged |
| `zero_for_one` | `bool` | true: `currency0` in, `currency1` out |
| `exact_amount` | `int` | exact **input**, in the input currency's units |

**Validation**: `exact_amount > 0`. A zero-size quote is not a price, and the
quoter itself rejects it.

## `Quote` (frozen)

| field | type | meaning |
|---|---|---|
| `request` | `QuoteRequest` | what was asked |
| `block` | `int` | the height the answer is true at |
| `amount_out` | `int` | output currency units |
| `gas_estimate` | `int` | the quoter's own estimate |

**Validation**: `amount_out > 0` — a quoter that returns zero without reverting
has not quoted; that is refused rather than stored.

`implied_price(quote) -> Decimal`: `amount_out / exact_amount` expressed as
*`currency1` per `currency0`* for both directions, inverting for `one_for_zero`,
so two quotes are comparable. Unit-bearing by construction: the two directions
would otherwise be reciprocals silently.

## `RefusalReason` (StrEnum)

`NOT_ENOUGH_LIQUIDITY`, `PRICE_LIMIT_ALREADY_EXCEEDED`, `UNKNOWN`.

Decoded from the inner selector of `UnexpectedRevertBytes(bytes)`. Each selector
is computed from its signature at import, never written as a literal.

## Exceptions

| type | means | never conflated with |
|---|---|---|
| `QuoteRefused` | the contract refused: carries `request`, `reason`, `named_pool_id` (where the payload carried one) and `raw` | anything numeric |
| `QuoteUnavailable` | the transport failed: a fact about the endpoint | `QuoteRefused` |
| `CurveDoesNotApply` | the tick path was asked for a pool whose class forbids it | a depth of zero |
| `NoTwoSidedMarket` | a mid was asked for and one side refused | a one-sided price |
| `WrongQuoter` | the quoter does not name the pool's manager | a revert |
| `QuoteNotCaptured` | a replay provider was asked for bytes it does not hold | an empty return |

`QuoteNotCaptured` matters as much as the rest: a replay that answered `0x` for
an unknown call would decode to `amount_out = 0`, and zero is the one answer this
whole requirement exists to forbid.

## Class gate

`CURVE_RECONSTRUCTIBLE = {STANDARD_CL, DYNAMIC_FEE_CL, HOOK_AUGMENTED_CL}`.

`require_curve_applies(key)` raises `CurveDoesNotApply` for `CUSTOM_ACCOUNTING`
and for `UNKNOWN` — §18.8.1 gives `UNKNOWN` "raw data only; exclude from
predictive depth features", which is the same prohibition arrived at differently.

The set is defined by listing what is permitted, not what is forbidden: a class
added later is excluded until somebody decides otherwise, which is the safe
direction to fail.
