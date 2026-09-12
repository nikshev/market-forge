---
id: OUT-2026-09-11-requirement-curve
step: requirement
records: [REQ-WP-046]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-046.md`, from PRD §18.9, §18.25 and §18.27's
seventh item, after reading `nikshev/copy-trade`'s Curve adapter and confirming
that both families are reachable on a public endpoint.

## What the survey settled

**The source repository has a Curve adapter and deliberately has no Curve
maths.** Its docstring is explicit: *"Rather than reimplement the fragile
per-type math (A scaling, rate/precision, variants), we call each pool's OWN
`get_dy` via eth_call."*

For an arbitrage bot quoting live state that is the correct decision, and it
does not transfer. A depth curve reconstructed from stored state at a past
event time has no contract to call — an archive node would be needed, and
reaching for the present instead is exactly what Principle I forbids. So the
view function here is the **authority the port is checked against**, not the
way the adapter answers.

That is the same relationship [[REQ-WP-045]] had with `getAmountOut`, and the
second time the survey's conclusion has been "this shortens the work and leaves
the careful part intact".

Two facts do carry over, both learned by that repository the hard way: the two
families answer **different `get_dy` signatures** (`int128` indices for
Stableswap, `uint256` for Cryptoswap), and a non-standard pool's `fee()` can
return a garbage word rather than reverting.

## What makes this verifiable

Three independent Ethereum endpoints answer without a key
(`ethereum-rpc.publicnode.com`, `eth.drpc.org`, `1rpc.io/eth`); two more that
are widely quoted do not, which is why the endpoint pool built for
[[OUT-2026-09-11-implement-slipstream]] transfers rather than the two-endpoint
pair before it.

Live pools exist in every family §18.9 asks to distinguish — a Stableswap-NG
plain pool, a factory Cryptoswap, a twocrypto-optimized, a tricrypto, the
original 3pool and a metapool — so the classification can be tested against
real instances of each rather than against constructed ones.

## What is deliberately deferred

- **Quoting *through* a metapool.** It is two quotes composed, and composing
  them belongs on top of a base-pool quote that is already verified.
- **The `CRYPTOSWAP_NG` generation**, until the classification distinguishes it
  from `CRYPTOSWAP` on a live pool rather than on a name.
