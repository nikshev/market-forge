---
id: OUT-2026-09-12-implement-curve-cryptoswap
step: implement
records: [REQ-WP-046]
commit: null
---

## What was done

`tools/record/cryptoswap_capture.py`, two chain-read fixtures and
`dex/cryptoswap.py` — tricrypto-ng's closed-form cubic, its cube roots, its
dynamic fee and its state bands. 87 tests, 32 of 40 mutants caught.

This closes [[REQ-WP-046]]. Status moves to `implemented`, with twocrypto
recorded as classified-but-not-quoted rather than approximated.

## Checking the version cost one call and saved the port

The deployed tricrypto pools report `version() == "v2.0.0"`, and
`tricrypto-ng`'s published `main` declares the same string. So the source read
is the source running.

**The sibling family does not line up.** The deployed twocrypto pool reports
`v3.0.0` while `twocrypto-ng`'s `main` says `v2.1.0`, and its `yb-init` tag —
the obvious candidate, since the pool is a Yield Basis pool — says `v2.1.0d`.
Twenty-odd branches, none of them the deployed contract. Porting from the
obvious place would have produced a module that matched a contract nobody runs.

So tricrypto is the half that landed. Twocrypto stays classified by
[[OUT-2026-09-11-implement-curve-stableswap-ng]]'s capability probe and is not
quoted, which is a gap worth naming rather than filling with the nearest source.

## Ninety quotes, ninety exact, and a second oracle that made that possible

Three live pools, six ordered index pairs each, five sizes spanning four
decades. All exact.

That result is less impressive than it sounds without the thing that produced
it. A quote here is a chain of a dozen steps — precisions, price scales, a cubic
in closed form with hand-rolled cube roots and a precision-juggling divider,
then a fee interpolated by how balanced the pool is. An end-to-end comparison
tells you the chain is wrong and nothing about where.

**The pool's maths library is a separate deployed contract**, and its `get_y`,
`cbrt` and `reduction_coefficient` are public views that take their own
arguments rather than a pool's. That makes it a second oracle *and* one that can
be asked about states no pool is in:

- nine solutions of the cubic on real state — exact;
- seventeen cube roots spanning all three of its scaling branches — exact;
- seven fee coefficients from balanced to a hundred to one — exact;
- **the cubic's negative branches and its Newton fallback**, reached by searching
  the input space and then asked of the chain.

That last one is the difference between "the source says it reverts here" and
"it reverts here". Both `b < 0` states found revert on chain even with a usable
discriminant; the non-positive-discriminant state does not revert, and the
fallback's answer is now a fixture.

## Two things about the EVM that had to be reproduced

- **`int256` division truncates toward zero; Python's `//` floors.** Several of
  the cubic's coefficients go negative, so the two disagree by one at every such
  step — and a coefficient wrong by one, cubed and rescaled, is not a rounding
  difference in the answer.
- **A division by zero yields zero rather than raising.** `cbrt(0)` reaches that,
  so the case is written out explicitly.

And one thing that is not what it looks like: `cube_root` returns `cbrt(x)`
scaled by 1e12, not a cube root. Its three scaling branches exist only to keep
an unchecked multiplication inside 256 bits, and the thresholds are
`2**256 // 1e36` and `2**256 // 1e18` to the digit.

## The sweep, and eight survivors each with a reason

32 of 40 caught. The eight are worth listing individually, because three
different things are going on and only one of them is a gap:

**Measured equivalent — the contract's comment is not reproducible.** Six and
eight cube-root refinements give results *identical* to seven on two hundred
thousand magnitudes. The source says six would not converge and eight would be
one too many; that could not be reproduced. The count stays at seven for
fidelity, and the claim is now recorded as unverified rather than repeated.

The seed's `1260/1000` remainder correction is a different story: it is
invisible on every round magnitude, and a search found an input where dropping
it moves the sixteenth significant digit. That input is in the fixture and the
mutant is caught.

**Computed and discarded.** The negative-sign branches of `b_cbrt` and
`second_cbrt` execute only from states the chain refuses, so a wrong sign there
changes a value that is thrown away. Kept, because the contract has them.

**Redundant with a later guard.** The early `D` and balance band checks, and the
negative-root check, are each covered by the final `y`-band check on every input
tried. They are kept for a reason a value comparison cannot see: they fail early
and name the actual problem, instead of failing late and blaming `y`.

The first attempt at catching them failed instructively — a `D`-out-of-band case
that also violated the balance band, and a balance-outlier case that put the
outlier at the index the contract *skips*. Both "worked" and proved nothing.

**One genuinely unexercised refusal.** The Newton fallback's non-convergence
raise: the single state that reaches the fallback converges.

## What is still open

- **Twocrypto quoting**, pending a published source that matches the deployed
  `v3.0.0`.
- **A pool mid-ramp in the fixture**, which would exercise the ramp refusal
  against a real state rather than a constructed one.
- **The nine other tests §18.25 requires per adapter** — reorg rollback,
  checkpoint/replay equivalence, gap failure — which belong to the adapter that
  wraps this arithmetic, not to the arithmetic.
