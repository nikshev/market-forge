"""The two HyperEVM pools the DEX panes read (REQ-WP-099).

# @trace: REQ-WP-099

Pinned, not discovered. They are [[REQ-WP-058]]'s measurement: the two busiest WHYPE/USDC pools on
chain 999, found by counting `Swap` emitters over 800 blocks, one a Uniswap v3 pool and one an
Algebra Integral pool that emit the identical `Swap` topic and are different protocols. Reading
`token0()` and the factory at start would cost calls into a node that rate limits within seconds, to
learn what has been fixed since the pools were deployed -- and a pool that stopped being the pair it
was would be a reason to look at this file, not to carry on.

**The protocol comes from here, never from the event** (REQ-WP-058).
"""

from __future__ import annotations

from collections.abc import Mapping

from channelflow.chain.hyperevm import PoolFamily, RegisteredPool

CHAIN_ID = 999
NETWORK = "hyperevm"
#: The `venue` the swaps are stored under: the chain, not any exchange.
VENUE = "hyperevm"

WHYPE = "0x5555555555555555555555555555555555555555"
USDC = "0xb88339cb7199b77e23db6e890353e22632ba630f"

#: ERC-20 decimals, read from the tokens on 2026-10-11 (WHYPE) and the issuer's documentation
# (USDC).
DECIMALS: Mapping[str, int] = {WHYPE: 18, USDC: 6}

POOLS: tuple[RegisteredPool, ...] = (
    RegisteredPool(
        address="0x6c9a33e3b592c0d65b3ba59355d5be0d38259285",
        family=PoolFamily.UNISWAP_V3,
        factory="0xff7b3e8c00e57ea31477c32a5b52a58eea47b072",
        token0=WHYPE,
        token1=USDC,
        tick_spacing=10,
        fee_pips=500,
    ),
    RegisteredPool(
        address="0xbe512f5881b85c48d9c17bc5bb2be047d156d696",
        family=PoolFamily.ALGEBRA_INTEGRAL,
        factory="0xf77bd082c627aa54591cf2f2eaa811fd1ab3b1f3",
        token0=WHYPE,
        token1=USDC,
        tick_spacing=5,
    ),
)

BY_ADDRESS: Mapping[str, RegisteredPool] = {pool.address: pool for pool in POOLS}

#: The pool whose active liquidity the pane shows. Liquidity is in the pool's own units and is not
#: comparable across pools (REQ-WP-063), so one is chosen: the Uniswap v3 pool, which carried 68 of
#: the 88 swaps of the two over 800 blocks on 2026-10-11.
LIQUIDITY_POOL = POOLS[0].address

#: The markets the pools price: HYPE against a dollar. The DEX features are keyed by
#: `(venue, symbol)` and HyperEVM has no bars, so they are written to these series' bars
#: (REQ-WP-099, plan decision 5): every HYPE market the deployment ingests, because the pane is
#: about the asset the pools price.
SERIES: tuple[tuple[str, str], ...] = (("bybit", "HYPEUSDT"), ("okx", "HYPE-USDT-SWAP"))
