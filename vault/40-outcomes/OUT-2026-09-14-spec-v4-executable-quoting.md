---
id: OUT-2026-09-14-spec-v4-executable-quoting
step: spec
records: [REQ-WP-071]
commit: null
---

## What was done

Specified [[REQ-WP-071]] as `specs/112-v4-executable-quoting/spec.md`, from a
capture of all four `CUSTOM_ACCOUNTING` pools in the v4 fixture at Ethereum
mainnet block 25975796.

## What was decided

**The tick kernel refuses these pools rather than the quoter overriding it.**
The alternative — let the kernel answer and prefer the quote where one exists —
leaves a zero-depth figure reachable, and three of the four pools produce
exactly that figure while two of them trade a whole ETH. A gate that raises
cannot be read past by accident.

**A refusal is a value the system carries, not an absence.** Both refusal
reasons in the fixture are decoded by name and keep their raw payload; an
unrecognised selector decodes to an explicit unknown, never to success. The
adapter never retries at a smaller size to turn a refusal into a number.

**A mid needs both sides.** Measured: `0xf7caa8ee…` and `0x5d10cbe0…` quote
ETH→token and refuse to buy back the exact amount they had just offered. Any
mid for those pools would be invented here rather than measured on chain, so
asking for one raises.

**The quoter is identified by the manager it names.** Verified by calling
`poolManager()` on both the quoter and the state reader; each named the
singleton that emitted the fixture's `Initialize` logs. A hard-coded per-chain
address would be recall, and this repository does not price on recall.

**Scope held to exact-input single-hop.** §18.8.1 asks for an executable quote,
not a router.

## What is still open

- Whether a `HOOK_AUGMENTED_CL` pool should also prefer the quoter once its hook
  is classified. §18.8.1 permits reconstruction there "after hook behavior is
  classified", and nothing classifies hook behaviour yet — out of scope here.
- The fixture pins one block. A second capture at a later block would show
  whether the two one-sided pools stay one-sided, which is a fact about
  launchpad hooks rather than about this adapter.
