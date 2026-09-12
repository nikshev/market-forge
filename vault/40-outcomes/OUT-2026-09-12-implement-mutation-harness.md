---
id: OUT-2026-09-12-implement-mutation-harness
step: implement
records: [REQ-INFRA-004]
commit: null
---

## What was done

`tools/mutate.py`, six specifications under `tests/mutations/`, a `make mutate`
target, a CI step, and 13 tests for the harness itself.

`make mutate` now reproduces every mutation number in this vault: **141 caught,
10 survived, in 251 seconds.** Per module, matching what was reported at the
time: Slipstream 23/0, Aerodrome family 4/0, Curve Stableswap-NG 34/1,
Cryptoswap 32/8, Uniswap v4 25/0, HyperCore 27/1.

## Three flaws, and the order they surfaced in is the interesting part

**The bytecode cache**, found yesterday in the HyperCore sweep and the reason
this work exists. Python validates `.pyc` on `(mtime, size)`, so two consecutive
mutants of identical size within one second reuse the first's bytecode. There is
now a test for it: two same-length mutants, the first caught and the second not,
and a stale cache reports both as caught.

**The missing baseline**, never hit and always available. Against a red suite
every mutant is "caught". A test writes a failing test into the fixture suite and
asserts the sweep refuses to start.

**A broken mutation is not a catch**, and this one surfaced *while building the
tool* — which is the best argument for having built it. Converting the sweeps to
files, the first writer used TOML's basic multi-line string, whose trailing
backslash is a line continuation that eats the next line's leading whitespace.
Every multi-line pattern lost its indentation. Those mutations produced
unparseable code; the module failed to import; the suite went red without running;
and all of them scored as caught.

That is the most emphatic possible result and it means nothing, which is exactly
the failure shape this project keeps meeting — a number that is positive, ordered
and believable. The tool now parses each mutated source before running anything,
and a collection error is reported as a broken mutation rather than a catch.

The tool then found a real instance in the existing sweeps: `pairing rule
dropped` in the Uniswap v4 specification deleted the body of a `for` loop. It had
been counted as caught since the day it was written.

**And it found one in its own test suite**, which was satisfying: the
same-size-mutants test originally used `x: int` → `x: Any`, and `Any` is not
imported in the fixture module, so the annotation raised at import.

## The part that was not a bug fix

**A survivor's reason is now an assertion with a date on it.** Every sweep here
ends with a few survivors and a paragraph saying why each is acceptable. Those
paragraphs were prose in outcome notes, and nothing checked whether they were
still true. A specification's `survives` field carries the reason; a survivor
without one fails the sweep, and a recorded survivor that starts being caught
fails it too.

The second direction is the valuable one. A mutant that begins failing means the
tests grew to cover a branch somebody had written off as unreachable — good news
that would otherwise go unnoticed while a stale explanation sat in the vault
reading like understanding.

Ten reasons are recorded today, and they are worth reading as a group: two
measured-equivalent cube-root iteration counts, three guards a later guard
already covers, two values the chain computes and discards, two unexercised
refusals, and one guard whose fallthrough already refuses.

## A slip of the same kind this project keeps recording

The tool was written before its specification, and `make validate` refused:
R1, `implemented` with no spec. Exactly what [[REQ-WP-043]] did. The spec was
written after and says so, rather than being backdated.

Worth noting which check caught it. The ladder — `specified` before `planned`
before `tested` — is a discipline the commands follow and not a gate the tooling
enforces; R1 is the one rung that *is* enforced, and it is the one that fired.

## What was deliberately not built

**Mutation generation.** The mutations are written by hand, one per way the
module could plausibly be wrong. An off-the-shelf engine would enumerate far more
and mean far less — the value has always been in choosing mutations that
correspond to mistakes a person would actually make, and that is the part that
needs judgement rather than tooling.

## What is still open

- **Sweeps for the modules that predate this**, which is most of them.
  Thirty-six outcome notes cite a sweep and six specifications exist. The rest
  ran from scripts that are gone, and their numbers stay unreproducible until
  somebody writes the specification.
- **The cost trigger** recorded in [[ADR-065]]: when the sweep takes longer than
  the rest of the gate, it moves to changed specifications only, or out of CI.
