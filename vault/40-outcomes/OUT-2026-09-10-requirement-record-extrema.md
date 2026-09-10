---
id: OUT-2026-09-10-requirement-record-extrema
step: requirement
records: [REQ-WP-029]
commit: null
---

## What was done

[[REQ-WP-029]] written from [[REQ-WP-028]]'s own open question — the sixth time
this session a mechanism has been built with nothing calling it.

## What was decided

- **The caller is written down as a requirement, again.** Each previous instance
  was closed the same way, and the alternative — building a seventh mechanism and
  noting that nothing calls that either — is the pattern this keeps refusing.
- **Through the bus.** [[REQ-INFRA-003]]'s outcome note is blunt about its own
  weakness: "one caller, one capability, proven by tests rather than by use". A
  second producer and a second pair of consumers is what makes it a seam instead
  of an abstraction, and this requirement is the first chance to find out whether
  it holds.
- **Detection gets its own pass over the same bars.** The runner owns its loop
  and offers no per-bar hook; adding one to feed a detector would change a
  component that has nothing to do with extrema. Principle VII is satisfied by
  the events being identical, not by the iteration being shared.
- **Per-bar publishing, not a flush at the end.** A live process attaching the
  same subscribers must see the same order, and a batch at the end would be a
  second path for replay only.

## What is still open

- **Whether the bus survives a second producer** is the interesting part and is
  not knowable until it is done. If it needs to change, that is a finding about
  the bus, and it will be recorded as one rather than absorbed.
- **The detector accumulates rather than calling back.** Candidates land on a
  list inside it, so publishing them per bar means noticing what was appended.
  Whether that reads honestly or awkwardly is a plan question.
