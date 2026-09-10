# Phase 0 — Research

## 1. What is hashed?

**Decision**: every dataclass field of the model — fitted state and
hyperparameters alike.

**Rationale**: a model is what it learned *and* how it was told to learn. Two
that landed on identical weights from different penalties behave differently on
the next dataset, and a hash merging them would certify a reproduction that is
not one.

## 2. Exact bytes or rounded?

**Decision**: exact — `struct.pack("<d", value)` for floats, `tobytes()` plus
dtype and shape for arrays.

**Rationale**: two fits differing in the last bit produce different
probabilities. Rounding them together would lie about the one thing the hash
exists to certify. A platform producing different bytes has produced a different
artifact, and the spec says so rather than pretending otherwise.

## 3. How is "fitted" known?

**Decision**: the `Model` protocol gains a `fitted` property.

**Rationale**: the three implementations signal it three different ways, and no
outside test covers all of them. The same reasoning `Transform.centered` was
given — a member with no default, so the author of the next model cannot skip
the question. Two stand-ins that carry predictions rather than learning them
answer `False`, which is the honest answer and keeps them out of the registry.

## 4. Is the length framing load-bearing?

**Decision**: yes, and it took a search to prove it.

Two plain string fields **cannot** collide: the field names absorbed between them
anchor every position. The first collision attempt therefore passed with the
framing removed — a test that asserted something true and not the thing it
claimed. A mapping has no such anchors: `{"a": "sb"}` and `{"as": "b"}` produce
byte-identical output unframed, because the tag that starts a value is
indistinguishable from the last character of a key. A model holding per-feature
scaler parameters is exactly that shape.
