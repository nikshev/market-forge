---
id: SPEC-067-record-extrema
requirement: REQ-WP-029
speckit_path: specs/067-record-extrema/spec.md
status: draft
---

## Summary

The extremum tables, the endpoint and the chart markers exist and nothing fills
them. The replay already turns bars into channel snapshots and signals; the
detector takes the same bars and produces candidates and confirmations.

Two things make this more than plumbing.

**One run should produce everything the chart reads.** A replay that wrote
channels and signals and left extrema to a separate process would give a reader
two pictures assembled from two runs, with nothing to say whether they agree.

**The bus gets a second producer.** [[REQ-INFRA-003]]'s own outcome note calls
its benefit "one caller, one capability, proven by tests rather than by use".
Whether a seam holds is not knowable from one consumer, and this is the first
chance to find out — with the pre-commitment that if it has to change, that is a
finding about the bus rather than a detail of this work.

A confirmation is published in the turn of the bar that confirmed it, not
flushed at the end. A live process attaching the same subscribers has to see the
same order, and a batch would be a second path that only replay takes.

## Links

- Requirement: [[REQ-WP-029]]
- The tables it fills: [[REQ-WP-028]]
- The replay it extends: [[REQ-PIPE-001]]
- The bus it tests: [[REQ-INFRA-003]]
