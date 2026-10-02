---
id: SPEC-123-ingest-resilience
requirement: REQ-WP-078
speckit_path: specs/123-ingest-resilience/spec.md
status: draft
---

## Summary

REQ-WP-076 was marked implemented with a green suite, and six days later one
venue in three was delivering. The spec treats the seven defects as one cause:
the tests exercised the pieces, and the faults were in the joins — an archive
prefix the wiring builds differently from the one its test builds, reader threads
that end without telling the session, a policy field that means a stream lifetime
for one venue and a client idle limit for the others. So each requirement is
stated at the seam, and any scenario that could pass against the broken wiring is
not counted. The archive gains the symbol in its key, because three processes on
one venue were overwriting each other and what was lost cannot be recovered.

## Links

- Requirement: [[REQ-WP-078]]
- Repairs: [[REQ-WP-076]]
