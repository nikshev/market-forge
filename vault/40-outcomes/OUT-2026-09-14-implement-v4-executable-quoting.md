---
id: OUT-2026-09-14-implement-v4-executable-quoting
step: implement
records: [REQ-WP-071]
commit: null
---

## What was done

Implemented [[REQ-WP-071]] — PRD §18.8.1's last unbuilt rule. `CUSTOM_ACCOUNTING`
pools are now priced by an executable quote and refused by the curve.

- `src/channelflow/dex/v4_quoting.py` — `ExecutableQuoter`, `QuoteRequest`,
  `Quote`, `implied_price`, `encode_exact_input_single`, `decode_refusal`,
  `RefusalReason`, and five exception types.
- `src/channelflow/dex/uniswap_v4.py` — `CURVE_RECONSTRUCTIBLE`,
  `CurveDoesNotApply`, `require_curve_applies`.
- `src/channelflow/chain/providers.py` — `CallReverted`, carrying the revert
  payload where the node sent one.
- `tests/unit/dex/replay_provider.py` — a `ChainDataProvider` answering from the
  captured fixture; `tests/unit/dex/test_v4_quoting.py` — 32 tests.
- `tests/mutations/v4_quoting.toml`, `tests/mutations/v4_curve_gate.toml`.

### RED, before any implementation existed

    $ .venv/bin/python -m pytest tests/unit/dex/test_v4_quoting.py -q
    ImportError while importing test module '.../tests/unit/dex/test_v4_quoting.py'.
    tests/unit/dex/test_v4_quoting.py:19: in <module>
        from channelflow.chain.providers import CallReverted
    E   ImportError: cannot import name 'CallReverted' from 'channelflow.chain.providers'
    1 error in 0.16s

Nothing the tests name existed. GREEN afterwards: 32 passed; whole suite 2581
passed including integration; `ruff` clean; `mypy --strict` clean over 217 files.

## What was decided

**The replay seam is the provider, not the adapter.** `ReplayProvider` answers
`eth_call` keyed on `(to, calldata)` built with the adapter's own encoder. So the
encoder, the ABI decoder and the revert unwrapping all run in CI, offline, and a
mis-encoded field misses the fixture loudly instead of quoting a different pool.
The mutation "tick spacing is packed into 24 bits instead of sign-extended" is
caught by exactly this: it changes the call data, the lookup misses, and
`QuoteNotCaptured` is raised. A replay that served decoded quotes would have
scored that mutation as caught by nothing.

**`ReplayProvider` never returns `"0x"`.** Empty return data decodes to
`amount_out = 0`, and zero is the one answer this requirement exists to forbid.
An uncaptured call raises.

**A refusal keeps everything it arrived with.** `QuoteRefused` carries the
decoded reason, the pool id the contract named where it named one, the decoded
arguments, and the raw payload. `decode_refusal` returns `UNKNOWN` for a payload
the endpoint never sent, one that is not our wrapper, one whose inner selector is
unrecognised, and one truncated mid-word — four different unreadable things, one
honest answer, and never a *different* recognised reason.

### The mutation sweep found two weak assertions

22 mutations, first run **20 caught, 2 survived**. Both survivors were weak
tests, and both are now killed by new tests rather than by a recorded excuse:

- *"a wrapper is not required"* — deleting the
  `UnexpectedRevertBytes` check. The test that should have caught it fed a bare
  `NotEnoughLiquidity` payload, which without the wrapper check fails to parse
  anyway and still returns `UNKNOWN`, so the assertion held for the wrong reason.
  The new test wraps a **well-formed** `NotEnoughLiquidity` in a *different*
  wrapper: with the guard it is `UNKNOWN`, without it the pool is reported as
  illiquid on some other contract's error. It also asserts the same bytes inside
  the real wrapper *are* read, so the test is about the wrapper rather than about
  an unparseable payload.
- *"a short return is decoded anyway"* — no test ever fed a short return. The new
  one parametrises `"0x"` and a single word; both must raise `QuoteUnavailable`.

Second run: **22 caught, 0 survived.**

### Corrections made during implementation

One test asserted `gas_estimate == 248722` for the 1 ETH rung. That figure is the
0.01 ETH rung's, carried over from the exploratory probe; the fixture says
253482. Corrected to the fixture.

## What is still open

**The gate is a door, not a chokepoint.** Nothing bridges a v4 pool into
`PoolState` today, so `require_curve_applies` cannot be forgotten by existing
code — only by code written later. `test_the_tick_path_calls_a_pool_that_absorbs_
an_ether_unmovable` pins the hazard: it builds the state, watches
`require_tick_map_complete` **pass**, and asserts `depth_to_bps` answers
`reachable=False, amount0=0, "the pool has no active liquidity, so its price
cannot be moved"` — for a pool the same fixture shows absorbing 1 ETH for
496412035653451820217981817 units. If a bridge is ever built, the gate belongs
inside it.

**One block.** The fixture pins 25975796. Whether the two one-sided pools stay
one-sided is a fact about launchpad hooks, and finding out means another capture.

**Exact-output and multi-hop are not implemented.** §18.8.1 asks for an executable
quote, not a router.
