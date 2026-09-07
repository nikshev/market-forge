---
id: OUT-2026-09-07-spec-domain-model
step: spec
records: [REQ-WP-002]
commit: null
---

## What was done

Specified REQ-WP-002 as `specs/004-domain-model/spec.md`: thirteen functional
requirements and seven success criteria, from a one-line acceptance criterion
("serialization fixtures stable").

## What was decided

- **Nanosecond timestamps and decimals must not be JSON numbers.** Checked
  rather than assumed: `event_time_ns` today is 1788794605256368000, which
  exceeds JavaScript's safe integer range by more than two orders of magnitude.
  Round-tripping it through a double drifts it by 128 ns. For a system whose
  premise is exact `event_time` ordering and no repainting, that is a
  correctness failure at the API boundary — and PRD §27 and §28 put a React UI
  on top of exactly that boundary. A `Decimal` as a JSON number loses precision
  the same way. FR-007 and FR-008 state the property; the Assumptions record
  that strings are how it is met, so a future non-JSON encoding is not excluded.
- **`PriceLevel` is defined here.** PRD §10 references it four times and never
  defines it. It is a price and a quantity, and FR-012 makes zero quantity
  representable because in a book delta that means the rung was removed — an
  obvious reading, but one an implementer could get wrong by rejecting zero as
  invalid.
- **Blockchain position goes in a separate `ChainMeta`**, not as optional fields
  on `EventMeta`. §9 says blockchain events "also include" block number,
  transaction index, log index and hash. Putting them on `EventMeta` would give
  every CEX trade four permanently-null fields; a separate structure keeps the
  common case clean. This follows ADR-003's reasoning rather than extending it.
- **Identity is a requirement, not a convenience.** PRD §11.2 states the tuples
  for duplicate detection, and FR-011 makes each event expose its own. Without
  it, deduplication would be reimplemented per call site.
- **Scope held to §10's seven events.** The extremum models of §13A.19 and the
  signal models of §21 are excluded: WP-002 says "canonical events", and those
  describe derived state rather than anything ingested. Pulling them in would
  make this feature unreviewable and would specify models whose engines do not
  exist.

## What is still open

- **`market_type` stays a free string.** PRD §5 names the universes but does not
  enumerate a closed set. Constraining it now would bind connectors that do not
  exist; the first connector that needs a fixed vocabulary should propose one.
- **No persistence or database mapping.** This feature defines shapes and proves
  round-trip stability. PRD §29's storage schemas are a separate concern, and
  §29.0 already requires backend specifics to stay behind adapters.
- **Whether fixtures should be checked into a golden directory shared with
  PRD §35.2's end-to-end fixtures.** §35.2 describes raw-to-signal streams;
  these are per-model. They may want to live together later.
