"""One-shot recorder for Curve Stableswap-NG pool state and the pool's own quotes.

# @trace: REQ-WP-046

PRD section 18.25 requires every protocol adapter's "quote curve matches
contract view within tolerance". A Curve pool exposes `get_dy(i, j, dx)` -- its
own answer to precisely the question the adapter computes -- so what this writes
is not a recording of what a venue said, it is the authority's answer.

Every read is pinned to one block. Stableswap-NG's quote depends on stored coin
rates, an amplification coefficient that may be mid-ramp, and a fee that moves
with how far off peg the pool sits; a fixture assembled across blocks would pair
one block's rates with another block's balances, and the adapter would be tested
against an arithmetic that never existed.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.curve_capture

Writes newline-delimited JSON under tests/fixtures/curve/. No credentials:
several Ethereum endpoints answer without a key, and `tools.record.evm` requires
two of them to agree on every value.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.record.evm import (
    EndpointPool,
    Reverted,
    answers,
    dyn_array,
    encode_address,
    encode_uint,
    selector,
    word,
)
from tools.record.evm import address as address_at

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "curve"

#: Endpoints that answer `eth_call` on Ethereum mainnet without a key, verified
#: one at a time. Four widely quoted ones do not and are left out rather than
#: left in to fail: `eth.llamarpc.com` (525), `rpc.ankr.com/eth` (demands
#: authentication), `rpc.flashbots.net` and `endpoints.omniatech.io` (403).
#:
#: Eight rather than three because this capture makes a few hundred calls and a
#: quorum of two is easy to lose to one rate limit late in a run.
RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://1rpc.io/eth",
    "https://eth.merkle.io",
    "https://eth-pokt.nodies.app",
    "https://gateway.tenderly.co/public/mainnet",
    "https://rpc.mevblocker.io",
    "https://eth.rpc.blxrbdn.com",
)

#: Stableswap-NG pools on Ethereum, chosen from Curve's own pool listing for
#: what they exercise rather than for size, and every fact about them read from
#: the chain below:
#:
#: * a two-coin pool of plain 18-decimal stablecoins -- the simple case;
#: * a two-coin pool holding an ERC4626 vault share, whose stored rate is
#:   therefore not 1e18 and moves;
#: * a two-coin pool of an accruing LST against its underlying;
#: * a three-coin pool -- section 18.25 asks for "multi-coin indices handled
#:   correctly", and a two-coin fixture cannot show that.
POOLS = (
    ("rlusd_usdc", "0xD001aE433f254283FeCE51d4ACcE8c53263aa186"),
    ("dola_susde", "0x744793B5110f6ca9cC7CDfe1CE16677c3Eb192ef"),
    ("oeth_weth", "0xcc7d5785AD5755B6164e21495E07aDb0Ff11C2A8"),
    ("hemibtc_cbbtc_wbtc", "0x66039342C66760874047c36943B1e2d8300363BB"),
)

#: Curve's `AddressProvider`, immutable and the documented entry point to every
#: other Curve registry. Its id 7 is the MetaRegistry, resolved live below
#: rather than hardcoded -- the provider is the stable address, the registries
#: behind it are not.
ADDRESS_PROVIDER = "0x0000000022D53366457F9d5E68Ec105046FC4383"
META_REGISTRY_ID = 7

#: What a pool answers, and what that means. Measured, not assumed: the first
#: attempt at this used `base_pool()` to spot a metapool and `get_dy_underlying`
#: as a backup, and neither works -- no metapool answers the first, and the
#: original 3pool answers the second. What actually separates a metapool is that
#: one of its coins is another pool's LP token, which is a fact about the
#: registry rather than about the pool, so it is read from the MetaRegistry.
CAPABILITY_PROBES = {
    "get_dy_int128": selector("get_dy(int128,int128,uint256)")
    + encode_uint(0)
    + encode_uint(1)
    + encode_uint(10**6),
    "get_dy_uint256": selector("get_dy(uint256,uint256,uint256)")
    + encode_uint(0)
    + encode_uint(1)
    + encode_uint(10**6),
    "offpeg_fee_multiplier": selector("offpeg_fee_multiplier()"),
    "gamma": selector("gamma()"),
    # Nullary for a two-coin Cryptoswap, indexed for a three-coin one: a pool
    # with three coins has two prices and no single scale to return.
    "price_scale": selector("price_scale()"),
    "price_scale_indexed": selector("price_scale(uint256)") + encode_uint(0),
}

#: One live instance of every shape section 18.9 asks to distinguish, plus one
#: contract that is not a Curve pool at all. Classification has to be tested
#: against real instances; a constructed one only tests the test.
FAMILY_SAMPLES = (
    ("stableswap-3pool", "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"),
    ("stableswap-steth", "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"),
    ("metapool-usd", "0xEd279fDD11cA84bEef15AF5D39BB4d4bEE23F0cA"),
    ("stableswap-ng-plain", "0xD001aE433f254283FeCE51d4ACcE8c53263aa186"),
    ("stableswap-ng-three", "0x66039342C66760874047c36943B1e2d8300363BB"),
    ("cryptoswap-factory", "0x47D5E1679Fe5f0D9f0A657c6715924e33Ce05093"),
    ("cryptoswap-twocrypto", "0x313698667d7FDD6789a9BC70821309ff891E729A"),
    ("cryptoswap-tricrypto", "0xf5f5B97624542D72A9E06f04804Bf81baA15e2B4"),
    ("not-a-pool-weth", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
)

#: How far behind the head to pin, so a reorg cannot move the fixture under us
#: between the read and the commit. Ethereum, so a dozen blocks is minutes.
CONFIRMATIONS = 12

#: Quote sizes, as a fraction of the sending coin's balance. Four decades, so a
#: port that is right at one size and wrong at another cannot pass -- the error
#: a curve's shape hides is precisely one that grows with the trade.
FRACTIONS = (1_000_000, 100_000, 10_000, 1_000, 100)


def _capabilities(pool_of: EndpointPool, address: str, registry: str, block: str) -> dict[str, Any]:
    observed = {
        name: answers(pool_of, address, data, block) for name, data in CAPABILITY_PROBES.items()
    }
    try:
        is_meta: bool | None = bool(
            word(
                pool_of.call(
                    registry, selector("is_meta(address)") + encode_address(address), block
                )
            )
        )
    except Reverted:
        # The registry does not know this address. That is an answer -- it is
        # not a Curve pool -- and it must not be flattened into False, which
        # would read as "a Curve pool that is not a metapool".
        is_meta = None
    return {"address": address.lower(), **observed, "is_meta": is_meta}


def main() -> None:
    pool_of = EndpointPool(RPCS)
    head = int(pool_of.any_rpc("eth_blockNumber", []), 16)
    block = hex(head - CONFIRMATIONS)
    print(f"pinned block {int(block, 16)}")

    registry = address_at(
        pool_of.call(
            ADDRESS_PROVIDER,
            selector("get_address(uint256)") + encode_uint(META_REGISTRY_ID),
            block,
        )
    )
    print(f"MetaRegistry {registry}")

    families = []
    for name, address in FAMILY_SAMPLES:
        observed = _capabilities(pool_of, address, registry, block)
        families.append({"name": name, "block": int(block, 16), **observed})
        answered = [key for key, value in observed.items() if value is True]
        print(f"  {name:>22} {answered} meta={observed['is_meta']}")

    records: list[dict[str, Any]] = []
    for name, pool in POOLS:
        n_coins = word(pool_of.call(pool, selector("N_COINS()"), block))
        coins = [
            address_at(pool_of.call(pool, selector("coins(uint256)") + encode_uint(i), block))
            for i in range(n_coins)
        ]
        rates = dyn_array(pool_of.call(pool, selector("stored_rates()"), block))
        balances = dyn_array(pool_of.call(pool, selector("get_balances()"), block))
        amplification = word(pool_of.call(pool, selector("A()"), block))
        fee = word(pool_of.call(pool, selector("fee()"), block))
        multiplier = word(pool_of.call(pool, selector("offpeg_fee_multiplier()"), block))

        quotes = []
        for i in range(n_coins):
            for j in range(n_coins):
                if i == j:
                    continue
                for fraction in FRACTIONS:
                    dx = balances[i] // fraction
                    if dx == 0:
                        continue
                    dy = word(
                        pool_of.call(
                            pool,
                            selector("get_dy(int128,int128,uint256)")
                            + encode_uint(i)
                            + encode_uint(j)
                            + encode_uint(dx),
                            block,
                        )
                    )
                    quotes.append({"i": i, "j": j, "dx": str(dx), "dy": str(dy)})

        records.append(
            {
                "name": name,
                "block": int(block, 16),
                "pool": pool.lower(),
                "n_coins": n_coins,
                "coins": coins,
                "stored_rates": [str(rate) for rate in rates],
                "balances": [str(balance) for balance in balances],
                "amplification": amplification,
                "fee": fee,
                "offpeg_fee_multiplier": multiplier,
                "quotes": quotes,
            }
        )
        print(
            f"  {name:>20} {pool} n={n_coins} A={amplification} fee={fee} "
            f"offpeg={multiplier} quotes={len(quotes)}"
        )

    FIXTURES.mkdir(parents=True, exist_ok=True)
    for filename, lines in (
        ("stableswap_ng.jsonl", records),
        ("families.jsonl", families),
    ):
        path = FIXTURES / filename
        path.write_text(
            "".join(
                json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n" for line in lines
            )
        )
        print(f"  {path.name}: {len(lines)}")


if __name__ == "__main__":
    main()
