"""One-shot recorder for Curve tricrypto-ng pool state, its quotes, and its maths.

# @trace: REQ-WP-046

PRD section 18.25 requires every adapter's "quote curve matches contract view
within tolerance". A tricrypto pool gives **two** independent views of the same
computation, and this records both:

* `get_dy(i, j, dx)` through the pool's view contract -- the whole quote,
  including the dynamic fee;
* `MATH.get_y(A, gamma, xp, D, i)` on the pool's own maths library -- the closed
  form cubic at the centre of it, with no fee and no scaling around it.

Two oracles matter here more than anywhere else in this project. The quote is a
long chain -- precisions, price scales, a cubic solved in closed form with
hand-rolled cube roots and a precision-juggling divider, then a fee interpolated
by how balanced the pool is. A single end-to-end comparison tells you the chain
is right or wrong and nothing about where.

**The version is established, not assumed.** The deployed pool reports
`version() == "v2.0.0"`, and `tricrypto-ng`'s published `main` declares the same
string, so the source read is the source running. That check is not ceremony: the
sibling `twocrypto-ng` deployment reports `v3.0.0` while its repository's `main`
says `v2.1.0`, so porting from the obvious place would have been porting the
wrong contract.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.cryptoswap_capture
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.record.evm import (
    EndpointPool,
    Reverted,
    encode_uint,
    selector,
    word,
)
from tools.record.evm import address as address_at

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "curve"

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

#: Live tricrypto-ng pools on Ethereum, from Curve's own pool listing. Three, so
#: a port that is right about one pool's scale and wrong about another's cannot
#: pass -- the coins here have 6, 8 and 18 decimals between them, which is where
#: a precision or a price scale gets dropped without any symptom.
POOLS = (
    ("tricrypto_usdt", "0xf5f5B97624542D72A9E06f04804Bf81baA15e2B4"),
    ("tricrypto_usdc", "0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B"),
    ("tricrypto_llama", "0x2889302a794dA87fBF1D6Db415C1492194663D13"),
)

N_COINS = 3
CONFIRMATIONS = 12

#: Quote sizes as a fraction of the sending coin's balance -- four decades.
FRACTIONS = (1_000_000, 100_000, 10_000, 1_000, 100)

#: Inputs to the maths library that no live pool's state reaches, and what the
#: chain answers for them. This is the point of recording the library separately
#: from the pool: `MATH.get_y` takes its arguments, not a pool's, so the closed
#: form's negative branches and its Newton fallback can be asked about directly
#: instead of being left uncovered because no real pool sits there.
#:
#: Each was found by searching the input space for a state that reaches one
#: branch, then confirmed against the chain here. `(A, gamma, xp, D, i)`.
SYNTHETIC_GET_Y = (
    (
        "b_negative",
        267196609,
        37028706146095596,
        (20886841324132681669106071, 79276318509905851657870693, 19298327176706273014998763),
        58877658798079032161340456,
        0,
    ),
    (
        # Both negative branches of the closed form -- a negative `b` and a
        # non-positive `delta1` -- with a discriminant the contract can still
        # use, so it reaches the sign-handling rather than the fallback. The
        # first attempt at this reached them with an unusable discriminant, and
        # the contract reverted before the signs mattered.
        "negative_b_and_delta1",
        204976003,
        48783136229731094,
        (6875878800128714148417709335, 3534938244668860668049757, 683848445482023401258791685),
        86650346490355185556439326,
        0,
    ),
    (
        "sqrt_nonpositive",
        238445997,
        30159375238739328,
        (3046971386573812099407593698, 104163565813415637265279191, 4708232393060166348335776),
        90464484474356291500422538,
        0,
    ),
    # Out of the band the contract asserts. Recorded as refusals: the adapter
    # must refuse exactly where the contract does, and "it reverted" is a fact
    # about the contract worth committing.
    ("A_below_band", 1, 30159375238739328, (10**24, 10**24, 10**24), 3 * 10**24, 0),
    ("A_above_band", 10**12, 30159375238739328, (10**24, 10**24, 10**24), 3 * 10**24, 0),
    ("gamma_below_band", 267196609, 1, (10**24, 10**24, 10**24), 3 * 10**24, 0),
    ("gamma_above_band", 267196609, 10**18, (10**24, 10**24, 10**24), 3 * 10**24, 0),
    ("D_below_band", 267196609, 30159375238739328, (10**24, 10**24, 10**24), 10**16, 0),
    # D above its band while every balance stays in band relative to it, so the
    # D check is the only one that can fire.
    ("D_above_band", 267196609, 30159375238739328, (10**34, 10**34, 10**34), 10**34, 0),
    # And the mirror: D in band, balances far from it. Note the index -- the
    # contract skips `i`, so the first attempt put the outlier at `i` and the
    # call went through, proving nothing.
    ("x_far_from_D", 267196609, 30159375238739328, (10**24, 10**30, 10**30), 10**24, 0),
)

#: Cube-root inputs spanning all three of the library's scaling branches, plus
#: values whose true cube root is irrational. The contract's `cbrt` is seven
#: unrolled Newton steps from a log-2 seed and is not a correctly rounded cube
#: root, so only the contract can say what it returns.
_CBRT_THRESHOLD = 115792089237316195423570985008687907853269
CBRT_INPUTS = (
    0,
    1,
    7,
    8,
    10**6,
    10**7 + 1,
    10**12,
    10**18,
    3 * 10**19 + 7,
    10**30 + 12345,
    10**42,
    _CBRT_THRESHOLD - 1,
    _CBRT_THRESHOLD,
    _CBRT_THRESHOLD + 1,
    _CBRT_THRESHOLD * 10**18 - 1,
    _CBRT_THRESHOLD * 10**18,
    _CBRT_THRESHOLD * 10**18 + 1,
    # The seed's remainder correction -- the `1260/1000` factor -- is invisible
    # on every value above: the seven refinements absorb it. This one it does
    # not, found by searching two hundred thousand magnitudes. Without it the
    # answer is off in its sixteenth significant digit, which is exactly the
    # kind of difference that survives a tolerance and fails an equality.
    1656850013097707493862586723483940562407847066138497172,
)

#: Balance triples and fee gammas for `reduction_coefficient`, from perfectly
#: balanced to a hundred to one.
REDUCTION_INPUTS = (
    ((10**18, 10**18, 10**18), 0),
    ((10**18, 10**18, 10**18), 10**15),
    ((10**20, 10**18, 10**18), 0),
    ((10**20, 10**18, 10**18), 10**13),
    ((10**20, 10**18, 10**18), 10**15),
    ((10**20, 10**18, 10**18), 10**17),
    ((2 * 10**18, 10**18, 10**18), 10**15),
)

#: Expected `version()`. A pool reporting anything else is not the contract this
#: adapter was written from, and the capture refuses rather than recording it.
EXPECTED_VERSION = "v2.0.0"


def _string_return(result: str) -> str:
    offset = word(result, 0) // 32
    length = word(result, offset)
    raw = result[2:][(offset + 1) * 64 : (offset + 1) * 64 + length * 2]
    return bytes.fromhex(raw).decode()


def _uint_array(result: str, count: int) -> list[int]:
    """A fixed-size `uint256[N]` return value, which is not offset-encoded."""
    return [word(result, index) for index in range(count)]


def main() -> None:
    pool_of = EndpointPool(RPCS)
    head = int(pool_of.any_rpc("eth_blockNumber", []), 16)
    block = hex(head - CONFIRMATIONS)
    print(f"pinned block {int(block, 16)}")

    records: list[dict[str, Any]] = []
    for name, pool in POOLS:
        version = _string_return(pool_of.call(pool, selector("version()"), block))
        if version != EXPECTED_VERSION:
            raise SystemExit(
                f"{name} reports {version!r}, not {EXPECTED_VERSION!r}: "
                "this is not the contract the adapter was ported from"
            )

        math = address_at(pool_of.call(pool, selector("MATH()"), block))
        precisions = _uint_array(pool_of.call(pool, selector("precisions()"), block), N_COINS)
        balances = [
            word(pool_of.call(pool, selector("balances(uint256)") + encode_uint(k), block))
            for k in range(N_COINS)
        ]
        price_scale = [
            word(pool_of.call(pool, selector("price_scale(uint256)") + encode_uint(k), block))
            for k in range(N_COINS - 1)
        ]
        amplification = word(pool_of.call(pool, selector("A()"), block))
        gamma = word(pool_of.call(pool, selector("gamma()"), block))
        invariant = word(pool_of.call(pool, selector("D()"), block))
        ramp_ends = word(pool_of.call(pool, selector("future_A_gamma_time()"), block))
        packed_fee = word(pool_of.call(pool, selector("packed_fee_params()"), block))
        mid_fee = word(pool_of.call(pool, selector("mid_fee()"), block))
        out_fee = word(pool_of.call(pool, selector("out_fee()"), block))
        fee_gamma = word(pool_of.call(pool, selector("fee_gamma()"), block))

        # The scaled balances the maths library actually sees. Recorded rather
        # than derived, so the fixture can tell a wrong quote apart from a wrong
        # scaling before the quote is even reached.
        xp = [balances[0] * precisions[0]]
        xp += [
            balances[k + 1] * price_scale[k] * precisions[k + 1] // 10**18
            for k in range(N_COINS - 1)
        ]

        quotes = []
        for i in range(N_COINS):
            for j in range(N_COINS):
                if i == j:
                    continue
                for fraction in FRACTIONS:
                    dx = balances[i] // fraction
                    if dx == 0:
                        continue
                    try:
                        dy = word(
                            pool_of.call(
                                pool,
                                selector("get_dy(uint256,uint256,uint256)")
                                + encode_uint(i)
                                + encode_uint(j)
                                + encode_uint(dx),
                                block,
                            )
                        )
                    except Reverted as exc:
                        # A trade large enough to leave the pool's safe band is
                        # refused by the contract. Recorded as a refusal, not
                        # dropped: the adapter must refuse the same inputs.
                        quotes.append({"i": i, "j": j, "dx": str(dx), "reverted": str(exc)[:80]})
                        continue
                    quotes.append({"i": i, "j": j, "dx": str(dx), "dy": str(dy)})

        # The second oracle: the closed form alone, on the untouched state, for
        # each coin index. No fee, no scaling back out.
        solved = []
        for index in range(N_COINS):
            payload = (
                selector("get_y(uint256,uint256,uint256[3],uint256,uint256)")
                + encode_uint(amplification)
                + encode_uint(gamma)
                + "".join(encode_uint(value) for value in xp)
                + encode_uint(invariant)
                + encode_uint(index)
            )
            try:
                result = pool_of.call(math, payload, block)
            except Reverted as exc:
                solved.append({"i": index, "reverted": str(exc)[:80]})
                continue
            solved.append({"i": index, "y": str(word(result, 0)), "k0": str(word(result, 1))})

        records.append(
            {
                "name": name,
                "block": int(block, 16),
                "pool": pool.lower(),
                "math": math,
                "version": version,
                "precisions": [str(value) for value in precisions],
                "balances": [str(value) for value in balances],
                "price_scale": [str(value) for value in price_scale],
                "xp": [str(value) for value in xp],
                "amplification": str(amplification),
                "gamma": str(gamma),
                "invariant": str(invariant),
                "future_a_gamma_time": ramp_ends,
                "packed_fee_params": str(packed_fee),
                "mid_fee": mid_fee,
                "out_fee": out_fee,
                "fee_gamma": fee_gamma,
                "quotes": quotes,
                "solved": solved,
            }
        )
        refused = sum(1 for quote in quotes if "reverted" in quote)
        print(
            f"  {name:>16} {pool} A={amplification} gamma={gamma} "
            f"mid={mid_fee} out={out_fee} quotes={len(quotes) - refused}(+{refused} refused) "
            f"solved={sum(1 for s in solved if 'y' in s)}/{N_COINS}"
        )

    # The maths library, asked about states no pool is in. Every pool in the
    # fixture points at the same library; one is enough.
    math = records[0]["math"]
    library: list[dict[str, Any]] = []
    for name, ann, gamma, xp_in, invariant, index in SYNTHETIC_GET_Y:
        payload = (
            selector("get_y(uint256,uint256,uint256[3],uint256,uint256)")
            + encode_uint(ann)
            + encode_uint(gamma)
            + "".join(encode_uint(value) for value in xp_in)
            + encode_uint(invariant)
            + encode_uint(index)
        )
        entry: dict[str, Any] = {
            "kind": "get_y",
            "name": name,
            "A": str(ann),
            "gamma": str(gamma),
            "xp": [str(value) for value in xp_in],
            "D": str(invariant),
            "i": index,
        }
        try:
            result = pool_of.call(math, payload, block)
            entry |= {"y": str(word(result, 0)), "k0": str(word(result, 1))}
        except Reverted:
            entry["reverted"] = True
        library.append(entry)
        print(f"  get_y {name:>18} -> {'reverted' if 'reverted' in entry else entry['y']}")

    for value in CBRT_INPUTS:
        result = pool_of.call(math, selector("cbrt(uint256)") + encode_uint(value), block)
        library.append({"kind": "cbrt", "x": str(value), "root": str(word(result))})

    for xp_in, fee_gamma in REDUCTION_INPUTS:
        payload = (
            selector("reduction_coefficient(uint256[3],uint256)")
            + "".join(encode_uint(value) for value in xp_in)
            + encode_uint(fee_gamma)
        )
        result = pool_of.call(math, payload, block)
        library.append(
            {
                "kind": "reduction_coefficient",
                "xp": [str(value) for value in xp_in],
                "fee_gamma": str(fee_gamma),
                "k": str(word(result)),
            }
        )
    print(f"  library rows: {len(library)}")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "tricrypto_math.jsonl"
    path.write_text(
        "".join(
            json.dumps(
                {"block": int(block, 16), "math": math, **row},
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for row in library
        )
    )
    print(f"  {path.name}: {len(library)}")

    path = FIXTURES / "tricrypto_ng.jsonl"
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records
        )
    )
    print(f"  {path.name}: {len(records)}")


if __name__ == "__main__":
    main()
